import { useCallback, useRef, useState } from "react";
import { aiChatStream } from "../api";
import type { AiMessage } from "../types";

interface ChatEvent {
  type: "text" | "tool_call" | "tool_result";
  name?: string;
  content?: string;
}

const EXAMPLES = [
  "What 10k resistors do I have in stock?",
  "Which parts are running low?",
  "Am I ready to build project X?",
  "What should I reorder from LCSC?",
  "Where are my STM32 microcontrollers?",
  "Show me all unassigned parts",
];

export default function AI() {
  const [messages, setMessages] = useState<AiMessage[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [thinking, setThinking] = useState(false);
  const [toolEvents, setToolEvents] = useState<ChatEvent[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = useCallback(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  const sendMessage = useCallback(
    async (text?: string) => {
      const msg = (text || input).trim();
      if (!msg || streaming) return;
      setInput("");
      setToolEvents([]);
      const userMsg: AiMessage = { role: "user", content: msg };
      setMessages((prev) => [...prev, userMsg]);
      setStreaming(true);
      setThinking(true);

      const assistantParts: string[] = [];
      const history = messages.map((m) => ({ role: m.role, content: m.content }));

      await aiChatStream(
        msg,
        history,
        (delta) => {
          setThinking(false);
          assistantParts.push(delta);
          setMessages((prev) => {
            const next = [...prev];
            const last = next[next.length - 1];
            if (last && last.role === "assistant") {
              next[next.length - 1] = {
                ...last,
                content: last.content + delta,
              };
            } else {
              next.push({ role: "assistant", content: delta });
            }
            return next;
          });
          scrollToBottom();
        },
        (name) => {
          setToolEvents((prev) => [...prev, { type: "tool_call", name }]);
          scrollToBottom();
        },
        (name, content) => {
          setToolEvents((prev) => [
            ...prev,
            { type: "tool_result", name, content },
          ]);
          scrollToBottom();
        },
        () => {
          setStreaming(false);
          setThinking(false);
        },
        (err) => {
          setStreaming(false);
          setThinking(false);
          setMessages((prev) => [
            ...prev,
            { role: "assistant", content: `Error: ${err.message}` },
          ]);
        },
      );
    },
    [input, messages, streaming, scrollToBottom],
  );

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="page ai-page">
      <header className="page-header">
        <h1>AI Assistant</h1>
        {messages.length > 0 && (
          <button
            className="btn btn-sm btn-outline"
            onClick={() => {
              setMessages([]);
              setToolEvents([]);
              setThinking(false);
            }}
          >
            Clear
          </button>
        )}
      </header>

      {messages.length === 0 && (
        <div className="ai-examples">
          <p className="muted">Ask me anything about your inventory.</p>
          <div className="ai-example-grid">
            {EXAMPLES.map((ex) => (
              <button
                key={ex}
                className="btn btn-outline btn-sm"
                onClick={() => sendMessage(ex)}
              >
                {ex}
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="ai-chat-log">
        {messages.map((m, i) => (
          <div key={i} className={`ai-msg ai-msg--${m.role}`}>
            <div className="ai-msg-role">{m.role === "user" ? "You" : "AI"}</div>
            <div className="ai-msg-content">{m.content}</div>
          </div>
        ))}
        {thinking && (
          <div className="ai-msg ai-msg--assistant">
            <div className="ai-msg-role">AI</div>
            <div className="ai-msg-content ai-thinking">
              <span className="ai-dot" />
              <span className="ai-dot" />
              <span className="ai-dot" />
            </div>
          </div>
        )}
        {streaming && toolEvents.length > 0 && (
          <div className="ai-tool-events">
            {toolEvents.map((ev, i) => (
              <div key={i} className="ai-tool-event">
                {ev.type === "tool_call" && (
                  <span className="muted">🔧 Calling {ev.name}…</span>
                )}
                {ev.type === "tool_result" && ev.content && (
                  <details className="ai-tool-result">
                    <summary className="muted">📋 {ev.name} result</summary>
                    <pre>{ev.content}</pre>
                  </details>
                )}
              </div>
            ))}
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="ai-input-bar">
        <textarea
          className="input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about your parts…"
          rows={1}
          disabled={streaming}
        />
        <button
          className="btn btn-primary"
          onClick={() => sendMessage()}
          disabled={streaming || !input.trim()}
        >
          {streaming ? "…" : "Send"}
        </button>
      </div>
    </div>
  );
}
