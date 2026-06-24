import { User, X } from "lucide-react";
import { useState } from "react";

const OCCASIONS = ["office", "wedding", "casual", "sports", "vacation", "party", "festive", "winter"];
const STYLES = ["formal", "smart casual", "ethnic", "streetwear", "minimalist", "boho", "athleisure"];

export default function UserProfilePanel({ profile, onChange, onClose }) {
  const [localProfile, setLocalProfile] = useState(profile || {
    gender: "",
    age: "",
    style_preferences: [],
  });

  const toggleStyle = (style) => {
    const current = localProfile.style_preferences || [];
    const updated = current.includes(style)
      ? current.filter((s) => s !== style)
      : [...current, style];
    const next = { ...localProfile, style_preferences: updated };
    setLocalProfile(next);
    onChange(next);
  };

  const handleChange = (field, value) => {
    const next = { ...localProfile, [field]: value };
    setLocalProfile(next);
    onChange(next);
  };

  return (
    <div className="w-72 shrink-0 bg-fashion-card border border-fashion-border rounded-2xl p-5 h-fit">
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-2">
          <User className="w-4 h-4 text-gold-400" />
          <h2 className="text-sm font-semibold text-white uppercase tracking-wider">My Style</h2>
        </div>
        <button onClick={onClose} className="text-fashion-muted hover:text-white transition-colors lg:hidden">
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Gender */}
      <div className="mb-4">
        <label className="text-xs text-fashion-muted uppercase tracking-widest mb-2 block">Gender</label>
        <div className="flex gap-2">
          {["men", "women"].map((g) => (
            <button
              key={g}
              onClick={() => handleChange("gender", localProfile.gender === g ? "" : g)}
              className={`flex-1 py-2 rounded-xl text-sm font-medium border transition-all ${
                localProfile.gender === g
                  ? "border-gold-400 text-gold-400 bg-gold-400/10"
                  : "border-fashion-border text-fashion-muted hover:border-gray-600"
              }`}
            >
              {g.charAt(0).toUpperCase() + g.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Age */}
      <div className="mb-4">
        <label className="text-xs text-fashion-muted uppercase tracking-widest mb-2 block">Age</label>
        <input
          type="number"
          placeholder="e.g. 24"
          value={localProfile.age || ""}
          onChange={(e) => handleChange("age", e.target.value)}
          className="w-full bg-[#0a0a0f] border border-fashion-border rounded-xl px-3 py-2 text-sm text-white placeholder-fashion-muted focus:outline-none focus:border-gold-400/50 transition-colors"
        />
      </div>

      {/* Style preferences */}
      <div>
        <label className="text-xs text-fashion-muted uppercase tracking-widest mb-2 block">Style Preferences</label>
        <div className="flex flex-wrap gap-2">
          {STYLES.map((style) => (
            <button
              key={style}
              onClick={() => toggleStyle(style)}
              className={`px-3 py-1 rounded-full text-xs border transition-all ${
                (localProfile.style_preferences || []).includes(style)
                  ? "border-gold-400 text-gold-400 bg-gold-400/10"
                  : "border-fashion-border text-fashion-muted hover:border-gray-600"
              }`}
            >
              {style}
            </button>
          ))}
        </div>
      </div>

      <p className="text-xs text-fashion-muted mt-4 leading-relaxed">
        These preferences help personalise recommendations. You can also just describe yourself in chat!
      </p>
    </div>
  );
}
