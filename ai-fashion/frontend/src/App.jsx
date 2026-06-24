import { useState, useRef, useEffect } from "react";
import { Send, Sparkles, User, Bot, SlidersHorizontal, X, Loader2 } from "lucide-react";
import { sendChatMessage } from "./services/api";
import OutfitRecommendation from "./components/OutfitRecommendation";
import UserProfilePanel from "./components/UserProfilePanel";

const SUGGESTIONS = [
  "I need an outfit for a business meeting",
  "Suggest a smart casual look for a dinner date",
  "I'm attending a wedding next weekend",
  "I'm a 22-year-old male looking for a casual summer outfit",
  "Something stylish for a beach vacation",
  "Give me a festive ethnic look for women",
];

function ChatMessage({ msg }) {
  const isUser = msg.role === "user";

  return (
    <div className={`flex gap-3 ${isUser ? "flex-row-reverse" : "flex-row"} mb-4`}>
      {/* Avatar */}
      <div
        className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${
          isUser ? "bg-gold-400/20 border border-gold-400/40" : "bg-purple-900/40 border border-purple-700/40"
        }`}
      >
        {isUser ? (
          <User className="w-4 h-4 text-gold-400" />
        ) : (
          <Sparkles className="w-4 h-4 text-purple-400" />
        )}
      </div>

      <div className={`flex flex-col gap-2 max-w-[85%] ${isUser ? "items-end" : "items-start"}`}>
        {/* Text bubble */}
        <div
          className={`px-4 py-2.5 rounded-2xl text-sm leading-relaxed ${
            isUser
              ? "bg-gold-400/10 border border-gold-400/20 text-white rounded-tr-sm"
              : "bg-fashion-card border border-fashion-border text-gray-200 rounded-tl-sm"
          }`}
        >
          {msg.content}
        </div>

        {/* Intent pills (only for assistant messages with intent) */}
        {!isUser && msg.intent && (
          <div className="flex flex-wrap gap-1.5 px-1">
            {msg.intent.gender && (
              <span className="px-2 py-0.5 rounded-full bg-blue-900/30 border border-blue-700/30 text-blue-300 text-xs">
                {msg.intent.gender}
              </span>
            )}
            {msg.intent.occasion && (
              <span className="px-2 py-0.5 rounded-full bg-purple-900/30 border border-purple-700/30 text-purple-300 text-xs">
                {msg.intent.occasion}
              </span>
            )}
            {msg.intent.style_keywords?.map((kw) => (
              <span key={kw} className="px-2 py-0.5 rounded-full bg-green-900/30 border border-green-700/30 text-green-300 text-xs">
                {kw}
              </span>
            ))}
          </div>
        )}

        {/* Outfit recommendation card */}
        {!isUser && msg.recommendation?.items?.length > 0 && (
          <div className="w-full">
            <OutfitRecommendation recommendation={msg.recommendation} />
          </div>
        )}
      </div>
    </div>
  );
}

export default function App() {
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content: "Hi! 👋 I'm your AI Fashion Stylist. Tell me about the occasion, your style, or what you're looking for — and I'll put together a complete outfit for you!",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [showProfile, setShowProfile] = useState(false);
  const [userProfile, setUserProfile] = useState({ gender: "", age: "", style_preferences: [] });
  const [conversationHistory, setConversationHistory] = useState([]);

  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async (text = input.trim()) => {
    if (!text || loading) return;

    const userMsg = { role: "user", content: text };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const profile = userProfile.gender || userProfile.age || userProfile.style_preferences?.length
        ? {
            gender: userProfile.gender || null,
            age: userProfile.age ? parseInt(userProfile.age) : null,
            style_preferences: userProfile.style_preferences,
          }
        : null;

      const data = await sendChatMessage(text, conversationHistory, profile);

      const assistantMsg = {
        role: "assistant",
        content: data.response_text,
        intent: data.intent,
        recommendation: data.recommendation,
      };

      setMessages((prev) => [...prev, assistantMsg]);
      setConversationHistory(data.conversation_history || []);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Sorry, something went wrong. Please make sure the backend is running and try again!",
        },
      ]);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="min-h-screen bg-fashion-dark flex flex-col">
      {/* ── Header ── */}
      <header className="border-b border-fashion-border px-6 py-4 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-gold-400/30 to-purple-600/30 border border-gold-400/20 flex items-center justify-center">
            <Sparkles className="w-4 h-4 text-gold-400" />
          </div>
          <div>
            <h1 className="font-display text-lg font-semibold gold-text leading-none">
              Dare XAI
            </h1>
            <p className="text-xs text-fashion-muted">AI Fashion Stylist</p>
          </div>
        </div>

        <button
          onClick={() => setShowProfile((p) => !p)}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-xl text-sm border transition-all ${
            showProfile
              ? "border-gold-400/40 text-gold-400 bg-gold-400/10"
              : "border-fashion-border text-fashion-muted hover:border-gray-600"
          }`}
        >
          {showProfile ? <X className="w-4 h-4" /> : <SlidersHorizontal className="w-4 h-4" />}
          <span className="hidden sm:inline">My Style</span>
        </button>
      </header>

      {/* ── Main area ── */}
      <div className="flex flex-1 overflow-hidden gap-4 p-4">
        {/* Chat */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Messages */}
          <div className="flex-1 overflow-y-auto pr-1 pb-4">
            {messages.map((msg, i) => (
              <ChatMessage key={i} msg={msg} />
            ))}

            {loading && (
              <div className="flex gap-3 mb-4">
                <div className="w-8 h-8 rounded-full bg-purple-900/40 border border-purple-700/40 flex items-center justify-center shrink-0">
                  <Sparkles className="w-4 h-4 text-purple-400" />
                </div>
                <div className="bg-fashion-card border border-fashion-border rounded-2xl rounded-tl-sm px-4 py-3 flex items-center gap-2">
                  <Loader2 className="w-4 h-4 text-gold-400 animate-spin" />
                  <span className="text-sm text-fashion-muted">Styling your outfit...</span>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Quick suggestions */}
          {messages.length <= 1 && (
            <div className="mb-3 flex flex-wrap gap-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => handleSend(s)}
                  className="px-3 py-1.5 rounded-full text-xs border border-fashion-border text-fashion-muted hover:border-gold-400/40 hover:text-gold-400 transition-all"
                >
                  {s}
                </button>
              ))}
            </div>
          )}

          {/* Input */}
          <div className="flex gap-3 items-end">
            <div className="flex-1 relative">
              <textarea
                ref={inputRef}
                rows={1}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Describe the occasion, your style, or what you need..."
                className="w-full bg-fashion-card border border-fashion-border rounded-2xl px-4 py-3 pr-12 text-sm text-white placeholder-fashion-muted resize-none focus:outline-none focus:border-gold-400/50 transition-colors leading-relaxed"
                style={{ minHeight: "48px", maxHeight: "120px" }}
              />
            </div>
            <button
              onClick={() => handleSend()}
              disabled={!input.trim() || loading}
              className="w-12 h-12 rounded-2xl bg-gold-400 hover:bg-gold-500 disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center transition-all shrink-0"
            >
              <Send className="w-4 h-4 text-black" />
            </button>
          </div>
        </div>

        {/* Profile sidebar */}
        {showProfile && (
          <div className="hidden lg:block">
            <UserProfilePanel
              profile={userProfile}
              onChange={setUserProfile}
              onClose={() => setShowProfile(false)}
            />
          </div>
        )}
      </div>
    </div>
  );
}
