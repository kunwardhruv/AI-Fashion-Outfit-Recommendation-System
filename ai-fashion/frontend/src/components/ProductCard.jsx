import { useState } from "react";
import { Star, IndianRupee } from "lucide-react";
import { getImageUrl } from "../services/api";

const ROLE_COLORS = {
  topwear:     "bg-blue-900/40 text-blue-300 border-blue-700/40",
  full_outfit: "bg-purple-900/40 text-purple-300 border-purple-700/40",
  bottomwear:  "bg-green-900/40 text-green-300 border-green-700/40",
  footwear:    "bg-orange-900/40 text-orange-300 border-orange-700/40",
  layer:       "bg-cyan-900/40 text-cyan-300 border-cyan-700/40",
  accessory:   "bg-pink-900/40 text-pink-300 border-pink-700/40",
};

export default function ProductCard({ product }) {
  const [imgError, setImgError] = useState(false);
  const [showScores, setShowScores] = useState(false);

  const imgUrl = getImageUrl(product.image);
  const roleColor = ROLE_COLORS[product.outfit_role] || "bg-gray-800 text-gray-400 border-gray-700";
  const scores = product.search_scores;

  // Show "Graph Pick" badge if compatibility graph recommended this item
  const isGraphPick = product.compatibility_source === "graph";

  return (
    <div className="card-hover bg-fashion-card border border-fashion-border rounded-2xl overflow-hidden flex flex-col">
      {/* Image */}
      <div className="relative w-full aspect-[3/4] bg-[#1a1a2e] overflow-hidden">
        {!imgError && imgUrl ? (
          <img
            src={imgUrl}
            alt={product.name}
            className="w-full h-full object-cover"
            onError={() => setImgError(true)}
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-4xl">
            {product.outfit_role === "footwear"    ? "👟" :
             product.outfit_role === "accessory"   ? "💍" :
             product.outfit_role === "full_outfit" ? "👗" :
             product.outfit_role === "bottomwear"  ? "👖" :
             product.outfit_role === "layer"       ? "🧥" : "👕"}
          </div>
        )}

        {/* Role badge */}
        <div className={`absolute top-2 left-2 px-2 py-0.5 rounded-full text-xs font-medium border ${roleColor}`}>
          {product.role_label || product.outfit_role}
        </div>

        {/* Graph Pick badge — shows when compatibility graph chose this item */}
        {isGraphPick && (
          <div className="absolute top-2 right-2 px-2 py-0.5 rounded-full text-xs font-medium bg-yellow-900/50 border border-yellow-600/40 text-yellow-300">
            🔗 Graph
          </div>
        )}

        {/* Score breakdown toggle — only shown for hybrid search results */}
        {scores && (
          <button
            onClick={() => setShowScores((s) => !s)}
            className="absolute bottom-2 right-2 px-2 py-0.5 rounded-full text-xs bg-black/60 border border-white/10 text-gray-300 hover:bg-black/80 transition-colors"
          >
            {showScores ? "Hide" : "Scores"}
          </button>
        )}

        {/* Score breakdown overlay */}
        {showScores && scores && (
          <div className="absolute bottom-0 left-0 right-0 bg-black/80 backdrop-blur-sm px-3 py-2 text-xs space-y-0.5">
            {/* 
              WHY 3 scores:
              text  = sentence-transformer semantic match
              image = CLIP visual match (cross-modal: text query → image embedding space)
              bm25  = keyword match
            */}
            <div className="flex justify-between text-blue-300">
              <span>📝 Text</span>
              <span>{(scores.text * 100).toFixed(0)}%</span>
            </div>
            <div className="flex justify-between text-purple-300">
              <span>🖼 Image</span>
              <span>{(scores.image * 100).toFixed(0)}%</span>
            </div>
            <div className="flex justify-between text-green-300">
              <span>🔤 BM25</span>
              <span>{(scores.bm25 * 100).toFixed(0)}%</span>
            </div>
          </div>
        )}
      </div>

      {/* Info */}
      <div className="p-3 flex flex-col gap-1 flex-1">
        <p className="text-xs text-fashion-muted uppercase tracking-widest font-medium">
          {product.brand}
        </p>
        <h3 className="text-sm font-medium text-white leading-snug line-clamp-2">
          {product.name}
        </h3>

        <div className="flex items-center gap-2 mt-auto pt-2">
          <span className="flex items-center gap-0.5 text-gold-400 font-semibold text-sm">
            <IndianRupee className="w-3 h-3" />
            {Number(product.price_inr).toLocaleString("en-IN")}
          </span>
          {product.rating && (
            <span className="flex items-center gap-0.5 text-xs text-fashion-muted ml-auto">
              <Star className="w-3 h-3 fill-gold-400 text-gold-400" />
              {Number(product.rating).toFixed(1)}
            </span>
          )}
        </div>

        <p className="text-xs text-fashion-muted line-clamp-2 leading-relaxed">
          {product.description}
        </p>
      </div>
    </div>
  );
}