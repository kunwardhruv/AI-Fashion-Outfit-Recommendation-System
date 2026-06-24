import axios from "axios";

const api = axios.create({
  baseURL: "/api",
  headers: { "Content-Type": "application/json" },
});

/**
 * Send a chat message and get outfit recommendation back.
 * @param {string} message - User's natural language request
 * @param {Array} conversationHistory - Previous messages [{role, content}]
 * @param {Object|null} userProfile - Optional {gender, age, style_preferences}
 */
export async function sendChatMessage(message, conversationHistory = [], userProfile = null) {
  const response = await api.post("/chat", {
    message,
    conversation_history: conversationHistory,
    user_profile: userProfile,
  });
  return response.data;
}

export async function getHealth() {
  const response = await api.get("/health");
  return response.data;
}

/**
 * Build the full image URL from a product's image path.
 * products.csv has paths like: images/ajio/469618352.jpg
 * Backend serves them at: /images/ajio/469618352.jpg
 */
export function getImageUrl(imagePath) {
  if (!imagePath) return null;
  // Strip leading "images/" since it's mounted at /images/
  const cleaned = imagePath.replace(/^images\//, "");
  return `/images/${cleaned}`;
}
