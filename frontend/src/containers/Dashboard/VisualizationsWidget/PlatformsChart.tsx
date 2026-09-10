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
import { Button, DropdownMenu } from "@radix-ui/themes";

interface PlatformMetrics {
    platform: string;
    technique_count: number;
}

interface OperationalAttributionProps {
    campaign?: Campaign | null;
}

const PlatformsChart: React.FC<OperationalAttributionProps> = ({ campaign }) => {
    const [data, setData] = useState<PlatformMetrics[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [showDescription, setShowDescription] = useState(false);

    useEffect(() => {
        if (!campaign) return;

        const fetchPlatformData = async () => {
            setLoading(true);
            setError(null);
            try {
                const res = await fetch(
                    `http://localhost:8000/api/campaigns/${campaign.id}/platform-technique-count/`,
                    { method: "GET" }
                );
                if (!res.ok) throw new Error(`HTTP error! Status: ${res.status}`);
                const json = await res.json();
                setData(json.data || []);
            } catch (err) {
                console.error(err);
                setError("Failed to load platform technique counts.");
            } finally {
                setLoading(false);
            }
        };

        fetchPlatformData();
    }, [campaign]);

    if (loading) return <div className="p-4">Loading...</div>;
    if (error) return <div className="p-4 text-red-600">{error}</div>;
    if (!data.length) return <div className="p-4">No platform data found.</div>;

    return (
        <div className="flex flex-col gap-4 h-full p-10">
            <h2 className="section-heading">
                Determine Platforms Targeted by <em className="text-blue-700">{campaign?.name}</em>
            </h2>

            {/* Toggle button for explanation */}
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

            {/* Description and Goal */}
            {showDescription && (
                <div className="text-sm text-gray-600 text-left mt-2">
                    <p>This chart shows all platforms targeted by techniques in the selected campaign.</p>
                    <ul className="list-disc ml-5 mt-1 space-y-1">
                        <li>
                            <strong>Platform Name</strong>: Each platform is displayed on the y-axis.
                        </li>
                        <li>
                            <strong>Technique Count</strong>: Number of techniques that target the platform.
                            Higher counts indicate more focus on that platform.
                        </li>
                    </ul>
                    <p className="mt-2 font-semibold text-gray-700">
                        Goal: Quickly identify which platforms the campaign primarily targets.
                    </p>
                    <p className="mt-2">
                        Example platforms (Enterprise domain):
                        <ul className="list-disc ml-5 mt-2">
                            <li><b>PRE</b>: systems or environments where attackers plan or test their actions before targeting real systems</li>
                            <li><b>Windows</b>: Microsoft desktop and server systems</li>
                            <li><b>macOS</b>: Apple Mac computers</li>
                            <li><b>Linux</b>: open-source servers and desktops</li>
                            <li><b>Cloud</b>: online infrastructure and storage</li>
                            <li><b>Office Suite</b>: productivity apps like Word or Excel</li>
                            <li><b>Identity Provider</b>: user authentication systems</li>
                            <li><b>SaaS</b>: cloud software apps like Salesforce</li>
                            <li><b>IaaS</b>: cloud infrastructure like AWS or Azure VMs</li>
                            <li><b>Network Devices</b>: routers, firewalls, switches</li>
                            <li><b>Containers</b>: isolated environments for apps, e.g., Docker</li>
                            <li><b>ESXi</b>: software for running multiple virtual computers</li>
                        </ul>
                        <span className="block mt-2">
                            Techniques from the ICS and Mobile domains, which focus on industrial machines like factory controllers or power systems and mobile devices like Android and iOS, are not included in the visualization.
                        </span>
                    </p>
                </div>
            )}

            <div className="flex-1">
                <ResponsiveContainer width="100%" height={Math.max(data.length * 50, 400)}>
                    <BarChart data={data} layout="vertical">
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis type="number" allowDecimals={false} />
                        <YAxis
                            type="category"
                            dataKey="platform"
                            width={200}
                        />
                        <Tooltip />
                        <Legend verticalAlign="top" align="right" />
                        <Bar dataKey="technique_count" fill="#276749" name="Technique Count" />
                    </BarChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
};

export default PlatformsChart;