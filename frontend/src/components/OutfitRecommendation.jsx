import { Sparkles, IndianRupee, Tag, Palette, GitBranch, Layers } from "lucide-react";
import ProductCard from "./ProductCard";

// Source labels with icons — tells user HOW the outfit was generated
const SOURCE_META = {
  curated: {
    label: "Stylist Pick",
    icon: "✨",
    desc: "Expert-curated outfit from our stylist database",
    color: "text-gold-400 border-gold-400/30 bg-gold-400/5",
  },
  hybrid_generated: {
    label: "AI Generated",
    icon: "🤖",
    desc: "Multi-modal hybrid search: text + CLIP image + BM25",
    color: "text-purple-300 border-purple-500/30 bg-purple-500/5",
  },
};

export default function OutfitRecommendation({ recommendation }) {
  if (!recommendation || !recommendation.items?.length) return null;

  const { theme, occasion, palette, explanation, items, total_price, source } = recommendation;
  const sourceMeta = SOURCE_META[source] || SOURCE_META["hybrid_generated"];

  // Count how many items were graph-recommended
  const graphPicks = items.filter((i) => i.compatibility_source === "graph").length;

  return (
    <div className="mt-3 rounded-2xl border border-fashion-border bg-fashion-card overflow-hidden">

      {/* ── Header ── */}
      <div className="px-4 py-3 border-b border-fashion-border">
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1">
            {/* Source badge */}
            <div className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs border mb-2 ${sourceMeta.color}`}>
              <span>{sourceMeta.icon}</span>
              <span className="font-medium">{sourceMeta.label}</span>
            </div>

            <h3 className="text-base font-semibold text-white font-display">
              {theme || occasion}
            </h3>

            <div className="flex items-center gap-3 mt-1 flex-wrap">
              {occasion && (
                <span className="flex items-center gap-1 text-xs text-fashion-muted">
                  <Tag className="w-3 h-3" />
                  {occasion.charAt(0).toUpperCase() + occasion.slice(1)}
                </span>
              )}
              {palette && (
                <span className="flex items-center gap-1 text-xs text-fashion-muted">
                  <Palette className="w-3 h-3" />
                  {palette}
                </span>
              )}
              {/* Show graph contribution if any items came from compatibility graph */}
              {graphPicks > 0 && (
                <span className="flex items-center gap-1 text-xs text-yellow-400/80">
                  <GitBranch className="w-3 h-3" />
                  {graphPicks} item{graphPicks > 1 ? "s" : ""} via compatibility graph
                </span>
              )}
              <span className="flex items-center gap-1 text-xs text-fashion-muted">
                <Layers className="w-3 h-3" />
                {items.length} pieces
              </span>
            </div>
          </div>

          {/* Total price */}
          {total_price > 0 && (
            <div className="text-right shrink-0">
              <p className="text-xs text-fashion-muted">Total</p>
              <p className="flex items-center gap-0.5 text-gold-400 font-semibold text-sm">
                <IndianRupee className="w-3 h-3" />
                {Math.round(total_price).toLocaleString("en-IN")}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* ── AI Explanation ── */}
      {explanation && (
        <div className="px-4 py-3 bg-[#0f0f1e] border-b border-fashion-border">
          <div className="flex gap-2">
            <Sparkles className="w-4 h-4 text-gold-400 shrink-0 mt-0.5" />
            <p className="text-sm text-gray-300 leading-relaxed italic">
              "{explanation}"
            </p>
          </div>
        </div>
      )}

      {/* ── Product Grid ── */}
      <div className="p-4 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
        {items.map((product, i) => (
          <ProductCard key={product.id || i} product={product} />
        ))}
      </div>

      {/* ── Source explanation (educational, good for demo) ── */}
      <div className="px-4 pb-3">
        <p className="text-xs text-fashion-muted/60 italic">
          {sourceMeta.desc}
          {graphPicks > 0 ? " · Compatibility graph used expert outfit co-occurrence data." : ""}
        </p>
      </div>
    </div>
  );
}