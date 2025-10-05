import React, { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { getRagStats, toggleRag, RagStatsResponse } from "../api/client";
import { Toggle } from "../components/ui/Toggle";
import { GlassCard } from "../components/GlassCard";

export default function Profile() {
  const { t } = useTranslation();
  const [ragStats, setRagStats] = useState<RagStatsResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadRagStats = async () => {
      try {
        const stats = await getRagStats();
        setRagStats(stats);
      } catch (error) {
        console.error("Failed to load RAG stats:", error);
      } finally {
        setLoading(false);
      }
    };

    loadRagStats();
  }, []);

  const handleRagToggle = async (enabled: boolean) => {
    try {
      // Optimistically update UI
      setRagStats(prev => prev ? { ...prev, enabled } : null);

      const result = await toggleRag(enabled);
      if (!result.success) {
        throw new Error("Toggle failed");
      }

      // Reload stats to get updated data
      const updatedStats = await getRagStats();
      setRagStats(updatedStats);
    } catch (error) {
      console.error("Failed to toggle RAG:", error);
      // Revert optimistic update on error
      const refreshedStats = await getRagStats();
      setRagStats(refreshedStats);
    }
  };

  return (
    <main className="p-4 space-y-6">
      <h1 className="text-2xl font-bold text-white">{t("profile.title")}</h1>

      {/* RAG Settings */}
      <GlassCard className="p-6">
        <h2 className="text-xl font-semibold text-white mb-4">
          {t("profile.rag.title")}
        </h2>

        <div className="space-y-6">
          {/* RAG Toggle */}
          <Toggle
            label={t("profile.rag.title")}
            description={t("profile.rag.description")}
            checked={ragStats?.enabled ?? false}
            onChange={handleRagToggle}
            className="py-4"
          />

          {/* RAG Statistics */}
          {loading ? (
            <div className="text-gray-400">
              {t("profile.rag.stats")}: Loading...
            </div>
          ) : ragStats ? (
            <div className="bg-black/20 rounded-lg p-4 space-y-2">
              <h3 className="font-medium text-white">
                {t("profile.rag.stats")}
              </h3>
              <div className="text-sm text-gray-300 space-y-1">
                {ragStats.stats ? (
                  <>
                    <div>
                      {t("profile.rag.chunks")}: {ragStats.stats.total_chunks}
                    </div>
                    <div>
                      {t("profile.rag.sources")}: {Object.keys(ragStats.stats.sources).length}
                    </div>
                  </>
                ) : (
                  <div className="text-red-400">
                    {(ragStats as RagStatsResponse).error || "Failed to load RAG statistics"}
                  </div>
                )}
                <div>
                  Status: {ragStats.enabled ? t("profile.rag.enabled") : t("profile.rag.disabled")}
                </div>
              </div>
            </div>
          ) : (
            <div className="text-red-400">
              {t("profile.rag.stats")}: Failed to load
            </div>
          )}
        </div>
      </GlassCard>

      {/* Placeholder for future settings */}
      <GlassCard className="p-6">
        <h2 className="text-xl font-semibold text-white mb-4">
          Other Settings
        </h2>
        <p className="text-gray-400">
          More settings will be available here soon...
        </p>
      </GlassCard>
    </main>
  );
}
