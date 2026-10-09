// ProjectState adapter for OpenCode: the same owner-words hooks the Claude Code
// host gets, driven through one shared tool, scripts/projectstate_hooks.py.
//
// The installer (in the Python tool) copies this file into an instance at
// .opencode/plugins/projectstate.js (OpenCode 1.18.32 auto-loads project plugins
// from that directory). At load it resolves the tool at <repo>/scripts/
// projectstate_hooks.py relative to its own location (plugin dir -> .opencode
// -> repo root); if the tool is missing the adapter quietly does nothing.
//
// What it does, mirroring the Claude Code host hooks:
//   1. record — on every owner (user-role) message, pass the typed text to the
//      tool's `record` command. Synthetic parts (injected context, compaction
//      continuations) and the adapter's own follow-up messages (marked with
//      FOLLOWUP_MARKER) are never recorded. The host cannot tell who typed a
//      message, so anything a human or an agent types into a session is
//      recorded as the owner's words — except in child sessions (see below).
//   2. brief — the tool's `brief` output is put in front of the model via the
//      experimental.chat.system.transform hook. The subprocess runs once per
//      session (source "startup") and the text is cached; the cached text is
//      then included in the system prompt of every request for that session.
//      After compaction (session.compacted event) the cache is dropped and the
//      tool is asked again with source "compact", so the owner's words survive
//      a compacted context.
//   3. stop — when a session goes idle (session.idle event), the tool's `stop`
//      command runs. If it answers {"decision": "block", "reason": ...}, the
//      reason is sent once as a follow-up user message through the SDK client
//      (session.promptAsync), prefixed with FOLLOWUP_MARKER so record skips it.
//      A chain triggered by a follow-up passes stop_hook_active=true and never
//      sends a second follow-up, mirroring Claude Code's Stop hook contract.
//      Note: this needs a server that outlives the turn. In the TUI (and
//      against `opencode serve` via `run --attach`) the follow-up is delivered;
//      a plain non-interactive `opencode run` disposes its in-process instance
//      within milliseconds of the turn, before the delivery can land.
//
// Child sessions (subagents): when the owner works through an orchestrating
// session, delegated `task` subagents run in sessions with a parentID, and the
// messages "typed" there are the orchestrating agent's words, not the owner's.
// record and stop are skipped for any session whose SDK lookup
// (client.session.get) shows a parentID; the answer is cached per session id
// and a failed lookup counts as a child (fail closed: never record agent words
// as the owner's, never inject a follow-up into a worker). brief is kept for
// child sessions on purpose: workers should see the owner's standing words.
//
// Every hook catches everything and subprocess calls are killed after 5
// seconds; a failing tool must never break or delay a session. Problems are
// logged on stderr with a [projectstate] prefix. No dependencies beyond what
// OpenCode (Bun) provides.
import { spawn } from "node:child_process"
import { existsSync } from "node:fs"
import { dirname, join, resolve } from "node:path"
import { fileURLToPath } from "node:url"

const FOLLOWUP_MARKER = "[projectstate:automated-followup]"
const TIMEOUT_MS = 5000
const MAX_STDOUT_BYTES = 262144
const MAX_SESSION_CACHE = 200
const FOLLOWUP_RETRIES = [0, 150, 400]

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

function resolveTool() {
  const here = dirname(fileURLToPath(import.meta.url))
  const root = resolve(here, "..", "..")
  const tool = join(root, "scripts", "projectstate_hooks.py")
  return existsSync(tool) ? tool : null
}

// Run `python3 <tool> <command>` with one JSON object on stdin; never throws.
function runTool(tool, command, payload) {
  return new Promise((done) => {
    let out = ""
    let err = ""
    let child = null
    let settled = false
    let timer = null
    const finish = (ok, note) => {
      if (settled) return
      settled = true
      clearTimeout(timer)
      try {
        if (child) child.kill("SIGKILL")
      } catch {}
      done({ ok, stdout: out, stderr: err, note })
    }
    try {
      child = spawn("python3", [tool, command], { stdio: ["pipe", "pipe", "pipe"] })
    } catch (error) {
      done({ ok: false, stdout: "", stderr: String(error), note: "spawn-failed" })
      return
    }
    timer = setTimeout(() => finish(false, "timeout"), TIMEOUT_MS)
    child.on("error", (error) => finish(false, String(error)))
    child.stdout.on("data", (data) => {
      out += data
      if (out.length > MAX_STDOUT_BYTES) finish(false, "stdout-too-large")
    })
    child.stderr.on("data", (data) => {
      err += data
      if (err.length > MAX_STDOUT_BYTES) err = err.slice(0, MAX_STDOUT_BYTES)
    })
    child.on("close", (code) => finish(code === 0, code === 0 ? "ok" : `exit-${code}`))
    try {
      child.stdin.write(JSON.stringify(payload))
      child.stdin.end()
    } catch (error) {
      finish(false, `stdin-failed: ${error}`)
    }
  })
}

export const ProjectStatePlugin = async ({ client, directory }) => {
  const tool = resolveTool()
  // Quiet problem log: into the server log when possible, stderr as fallback.
  const log = (message) => {
    try {
      console.error(`[projectstate] ${message}`)
    } catch {}
    try {
      void client.app.log({
        body: { service: "projectstate", level: "warn", message: String(message) },
      })
    } catch {}
  }
  if (!tool) {
    log("scripts/projectstate_hooks.py not found at the plugin root; adapter disabled")
    return {}
  }

  // sessionID -> brief text, one subprocess call per session ("startup",
  // refreshed with "compact" after compaction). Insertion-ordered, capped.
  const briefs = new Map()
  // sessionID -> true (child/subagent) or false (primary), resolved once via
  // client.session.get and cached; a failed lookup caches "child" (fail closed).
  const childCache = new Map()
  // Sessions whose current stop chain already received one follow-up.
  const followupSent = new Set()

  function rememberChild(sessionID, child) {
    childCache.set(sessionID, child)
    if (childCache.size > MAX_SESSION_CACHE) {
      const oldest = childCache.keys().next().value
      if (oldest !== undefined) childCache.delete(oldest)
    }
  }

  async function isChildSession(sessionID) {
    const cached = childCache.get(sessionID)
    if (cached !== undefined) return cached
    try {
      const response = await client.session.get({ path: { id: sessionID } })
      const info = (response && response.data) || null
      const parentID = info && info.parentID
      rememberChild(sessionID, typeof parentID === "string" && parentID.length > 0)
    } catch (error) {
      log(`session lookup failed for ${sessionID}; treating it as a child`)
      rememberChild(sessionID, true)
    }
    return childCache.get(sessionID)
  }

  async function getBrief(sessionID, source) {
    const cached = briefs.get(sessionID)
    if (cached !== undefined) return cached
    const result = await runTool(tool, "brief", {
      hook_event_name: "SessionStart",
      cwd: directory,
      session_id: sessionID,
      source: source,
    })
    if (!result.ok) {
      log(`brief (${source}) failed: ${result.note}`)
      return ""
    }
    briefs.set(sessionID, result.stdout)
    if (briefs.size > MAX_SESSION_CACHE) {
      const oldest = briefs.keys().next().value
      if (oldest !== undefined) briefs.delete(oldest)
    }
    return result.stdout
  }

  return {
    "chat.message": async (input, output) => {
      try {
        const parts = (output.parts || []).filter(
          (part) => part && part.type === "text" && !part.synthetic && !part.ignored,
        )
        const text = parts.map((part) => part.text).join("\n")
        if (!text.trim()) return
        if (text.includes(FOLLOWUP_MARKER)) return
        // Child sessions carry an orchestrating agent's words, not the owner's.
        if (await isChildSession(input.sessionID)) return
        // A fresh owner turn starts a new stop chain.
        followupSent.delete(input.sessionID)
        await runTool(tool, "record", {
          hook_event_name: "UserPromptSubmit",
          cwd: directory,
          session_id: input.sessionID,
          prompt: text,
        })
      } catch (error) {
        log(`record failed: ${error}`)
      }
    },

    "experimental.chat.system.transform": async (input, output) => {
      try {
        const sessionID = input && input.sessionID
        if (!sessionID) return
        const text = await getBrief(sessionID, "startup")
        if (text && text.trim()) output.system.push(text)
      } catch (error) {
        log(`brief inject failed: ${error}`)
      }
    },

    event: async ({ event }) => {
      try {
        const type = event && event.type
        const props = (event && event.properties) || {}
        const sessionID = props.sessionID || (props.info && props.info.id)
        if (!sessionID) return

        if (type === "session.compacted") {
          // The compacted context no longer carries the brief; ask again with
          // source "compact" so the next request is warmed before it starts.
          briefs.delete(sessionID)
          await getBrief(sessionID, "compact")
          return
        }
        if (type !== "session.idle") return
        // Never gate a worker's turn on the owner's stop chain: subagents are
        // driven by their orchestrator, not by ProjectState.
        if (await isChildSession(sessionID)) return

        const alreadyChained = followupSent.has(sessionID)
        const result = await runTool(tool, "stop", {
          hook_event_name: "Stop",
          cwd: directory,
          session_id: sessionID,
          stop_hook_active: alreadyChained,
        })
        if (!result.ok) {
          log(`stop failed: ${result.note}`)
          return
        }
        if (alreadyChained) return
        let decision = null
        try {
          decision = JSON.parse(result.stdout)
        } catch {}
        if (!decision || decision.decision !== "block") return
        if (typeof decision.reason !== "string" || !decision.reason.trim()) return
        followupSent.add(sessionID)
        const body = {
          path: { id: sessionID },
          query: { directory },
          body: {
            parts: [{ type: "text", text: `${FOLLOWUP_MARKER} ${decision.reason}` }],
          },
        }
        for (const delay of FOLLOWUP_RETRIES) {
          if (delay) await sleep(delay)
          try {
            await client.session.promptAsync(body)
            break
          } catch (error) {
            if (delay === FOLLOWUP_RETRIES[FOLLOWUP_RETRIES.length - 1]) {
              log(`follow-up delivery failed for ${sessionID}: ${error}`)
            }
          }
        }
      } catch (error) {
        log(`event failed: ${error}`)
      }
    },
  }
}

export default ProjectStatePlugin
