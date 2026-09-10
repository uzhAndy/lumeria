import React, { useEffect, useState } from "react";
import {
    BarChart,
    Bar,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend,
    ResponsiveContainer,
} from "recharts";
import type { Campaign } from "../../../types/campaign.ts";
import { Tooltip as RadixTooltip, TooltipTrigger, TooltipContent } from "@radix-ui/react-tooltip";
import { InfoCircledIcon } from "@radix-ui/react-icons";
import { DropdownMenu, Button } from "@radix-ui/themes";

interface TechniqueMetrics {
    technique_name: string;
    mitigation_count: number;
    tactic_count?: number;
    usage_count?: number;
    created_date?: string | null;
    usage_summary?: string;
}

interface OperationalAttributionProps {
    campaign?: Campaign | null;
}

type OrderBy = "name" | "created_date" | "mitigation" | "tactic" | "usage";

const TechniquesChart: React.FC<OperationalAttributionProps> = ({ campaign }) => {
    const [data, setData] = useState<TechniqueMetrics[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [orderBy, setOrderBy] = useState<OrderBy>("created_date");
    const [showMitigation, setShowMitigation] = useState(true);
    const [showTactic, setshowTactic] = useState(false);
    const [showCreationDate, setShowCreationDate] = useState(true);
    const [showUsage, setShowUsage] = useState(true);
    const [totalCampaigns, setTotalCampaigns] = useState<number>(0);
    const [showDescription, setShowDescription] = useState(false);

    useEffect(() => {
        if (!campaign) return;

        const fetchMetrics = async () => {
            setLoading(true);
            setError(null);

            const payload = {
                show_mitigation: showMitigation,
                show_tactic: showTactic,
                show_usage: showUsage,
                order_by: orderBy,
            };

            try {
                console.log("vis payload: ", payload)
                const res = await fetch(
                    `http://localhost:8000/api/campaigns/${campaign.id}/technique_visualization-data/`,
                    {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify(payload),
                    }
                );

                if (!res.ok) {
                    throw new Error(`HTTP error! Status: ${res.status}`);
                }

                const json = await res.json();
                setData(json.techniques || []);
                setTotalCampaigns(json.total_campaigns || 0);
                console.log(json);
            } catch (err) {
                console.error(err);
                setError("Failed to load technique metrics.");
            } finally {
                setLoading(false);
            }
        };

        fetchMetrics();
    }, [campaign, showMitigation, showTactic, showUsage, orderBy]);

    if (loading) return <div className="p-4">Loading...</div>;
    if (error) return <div className="p-4 text-red-600">{error}</div>;
    if (!data.length) return <div className="p-4">No techniques found.</div>;

    const chartData = data.map((t) => ({
        ...t,
        technique_label: showCreationDate
            ? `${t.technique_name}, ${t.created_date ? new Date(t.created_date).toLocaleString('default', { month: 'short', year: 'numeric' }) : "unknown"}`
            : t.technique_name,
    }));

    return (
        <div className="flex flex-col gap-4 h-full p-10">
            <h2 className="section-heading">
                Technique Visualizations for <em className={"text-blue-700"}>{campaign?.name}</em>
            </h2>
            {/* Toggle button */}
            <div className="w-fit">
                <Button
                    variant="outline"
                    color="gray"
                    highContrast
                    size="2"
                    onClick={() => setShowDescription(!showDescription)}
                >
                    About this Visualization
                    <DropdownMenu.TriggerIcon />
                </Button>
            </div>

            {/* Short description and goal */}
            {showDescription && (
                <div className="text-sm text-gray-600 text-left">
                    <p>
                        This chart visualizes the techniques used in the selected campaign across several key metrics:
                    </p>

                    <ul className="list-disc ml-5 mt-1 space-y-1">
                        <li>
                            <strong>Technique & Creation Date</strong>: Name of the technique and when it was first observed.
                            Sorting by creation date helps find newly added techniques that may not yet be well mitigated or detected.
                        </li>
                        <li>
                            <strong>Mitigation Count</strong>: Number of mitigations applied to each technique.
                            This helps identify techniques that are under-protected and may require additional defenses.
                        </li>
                        <li>
                            <strong>Tactic Count</strong>: Number of tactics each technique contributes to.
                            Some techniques can be used for multiple tactics, making them more versatile and impactful.
                            This column helps prioritize techniques that affect several attack goals.
                        </li>
                        <li>
                            <strong>Usage Across Campaigns</strong>: Number of campaigns that use the techniques in this campaign.
                            There are <strong>{totalCampaigns}</strong> campaigns in total.
                            Sorting by usage highlights techniques unique to this campaign or rarely used elsewhere.
                        </li>
                    </ul>

                    <p className="mt-2 font-semibold text-gray-700">
                        Goal: Quickly identify under-protected, high-impact, or unique techniques to prioritize detection and mitigation strategies.
                    </p>
                </div>
            )}
            {/* Controls */}
            <div className="flex gap-4 items-center">
                <label className="flex items-center">
                    Order by:{" "}
                    <RadixTooltip>
                        <TooltipTrigger asChild>
                            <InfoCircledIcon className="w-5 text-gray-500 cursor-pointer mr-3" />
                        </TooltipTrigger>
                        <TooltipContent side="top" className="bg-white rounded px-2 py-1 text-xs border border-gray-400">
                            Select the column to sort techniques by:
                            <ul className="ml-4 mt-1">
                                <li><strong>Creation Date</strong>: find newest techniques</li>
                                <li><strong>Mitigation Count</strong>: find techniques with few mitigations</li>
                                <li><strong>Tactic Count</strong>: find techniques used in many tactics</li>
                                <li><strong>Technique Name</strong>: alphabetical order</li>
                            </ul>
                        </TooltipContent>
                    </RadixTooltip>
                    <select
                        value={orderBy}
                        onChange={(e) => setOrderBy(e.target.value as OrderBy)}
                        className="border rounded px-2 py-1"
                    >
                        <option value="created_date">Creation Date</option>
                        <option value="mitigation">Mitigation Count</option>
                        <option value="tactic">Tactic Count</option>
                        <option value="usage">Usage Across Campaigns</option>
                        <option value="name">Technique Name</option>
                    </select>
                </label>

                <label className="flex items-center gap-1">
                    <input
                        type="checkbox"
                        checked={showCreationDate}
                        onChange={(e) => setShowCreationDate(e.target.checked)}
                    />
                    Show Creation Date
                </label>

                <label className="flex items-center gap-1">
                    <input
                        type="checkbox"
                        checked={showMitigation}
                        onChange={(e) => setShowMitigation(e.target.checked)}
                    />
                    Show Mitigation
                </label>

                <label className="flex items-center gap-1">
                    <input
                        type="checkbox"
                        checked={showTactic}
                        onChange={(e) => setshowTactic(e.target.checked)}
                    />
                    Show Tactic
                </label>
                <label className="flex items-center gap-1">
                    <input
                        type="checkbox"
                        checked={showUsage}
                        onChange={(e) => setShowUsage(e.target.checked)}
                    />
                    Show Global Usage
                </label>
            </div>

            {/* Chart */}
            <div className="flex-1">
                <ResponsiveContainer width="100%" height={Math.max(data.length * (showCreationDate ? 50 : 35), 500)}>
                    <BarChart data={chartData} layout="vertical">
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis type="number" allowDecimals={false}/>

                        <YAxis
                            type="category"
                            dataKey="technique_label"
                            width={200}
                            interval={0}
                            tick={({ x, y, payload }) => {
                                const maxLineLength = 25; // truncating techniques names as some are too long for displaying
                                const lines = payload.value.split(', ').map((line: string) =>
                                    line.length > maxLineLength ? line.slice(0, maxLineLength) + ".." : line
                                );
                                return (
                                    <text x={x} y={y} textAnchor="end" fontSize={14}>
                                        {lines.map((line: string, index: number) => (
                                            <tspan key={index} x={x} dy={index === 0 ? 0 : 15}>
                                                {line}
                                            </tspan>
                                        ))}
                                    </text>
                                );
                            }}
                        />
                        <Tooltip
                            content={({ active, payload }) => {
                                if (!active || !payload || !payload.length) return null;

                                const data = payload[0].payload as TechniqueMetrics;

                                return (
                                    <div className="bg-white border rounded p-2 shadow-md max-w-xs">
                                        <p className="font-semibold">{data.technique_name}</p>

                                        {showMitigation && (
                                            <p className="text-sm">Mitigations: {data.mitigation_count}</p>
                                        )}

                                        {showTactic && (
                                            <p className="text-sm">Tactics: {data.tactic_count}</p>
                                        )}

                                        {showUsage && (
                                            <p className="text-sm">
                                                Used in campaigns: {data.usage_count}
                                            </p>
                                        )}

                                        {data.usage_summary && (
                                            <p className="text-sm text-gray-600 mt-1">
                                                <strong>Usage in this campaign:</strong><br />
                                                {data.usage_summary}
                                            </p>
                                        )}
                                    </div>
                                );
                            }}
                        />
                        <Legend
                            verticalAlign="top"
                            align="right"
                        />
                        {showMitigation && <Bar dataKey="mitigation_count" fill="#38a169" name="Mitigation Count" />}
                        {showTactic && <Bar dataKey="tactic_count" fill="#3182ce" name="Tactic Count" />}
                        {showUsage && <Bar dataKey="usage_count" fill="#F58518" name="Usage Across Campaigns" />}
                    </BarChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
};

export default TechniquesChart;