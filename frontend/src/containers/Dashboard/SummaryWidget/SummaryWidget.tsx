import React, { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import rehypeSanitize from "rehype-sanitize";
import remarkGfm from "remark-gfm";
import remarkBreaks from "remark-breaks";

import type {Campaign} from "../../../types/campaign.ts";

interface SummaryWidgetProps {
    campaign?: Campaign | null;
}

const SummaryWidget: React.FC<SummaryWidgetProps> = ({ campaign }) => {
    const [summary, setSummary] = useState<string>("");
    const [loading, setLoading] = useState<boolean>(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (!campaign) return;

        const fetchSummary = async () => {
            setLoading(true);
            setError(null);
            try {
                const res = await fetch(
                    `http://localhost:8000/api/campaigns/${campaign.id}/summary/`,
                    {
                        method: "GET",
                        headers: { "Content-Type": "application/json" },
                    }
                );
                const data = await res.json();
                setSummary(data.text || "No summary available.");
                console.log(data);
            }
            finally {
                setLoading(false);
            }
        };

        fetchSummary().catch((err) => {
            console.error("Unhandled fetchSummary error:", err);
            setError("Could not fetch summary.");
        });
    }, [campaign]);

    return (
        <div className="flex flex-col h-full rounded p-10">
            <h2 className="section-heading">
                Executive Summary for{" "}
                <em className="text-blue-700">{campaign?.name || "..."}</em>
            </h2>

            {loading && <p>Loading summary...</p>}
            {error && <p className="text-red-600">{error}</p>}

            {!loading && !error && summary && (
                <div className="text-left prose max-w-none">
                    <ReactMarkdown
                        remarkPlugins={[remarkGfm, remarkBreaks]}
                        rehypePlugins={[rehypeSanitize]}
                    >
                        {summary}
                    </ReactMarkdown>
                </div>
            )}
        </div>
    );
};

export default SummaryWidget;