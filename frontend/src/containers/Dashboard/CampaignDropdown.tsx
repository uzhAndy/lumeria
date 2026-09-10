import {useEffect, useMemo, useState} from "react";
import {Button} from "@radix-ui/themes";
import * as Popover from "@radix-ui/react-popover";
import {formatDistanceToNow} from "date-fns";
import type {Campaign} from "../../types/campaign.ts";

interface CampaignDropdownProps {
    selectedCampaign: Campaign | null;
    setSelectedCampaign: (campaign: Campaign) => void;
}

const CampaignDropdown: React.FC<CampaignDropdownProps> = ({
                                                               selectedCampaign,
                                                               setSelectedCampaign,
                                                           }) => {
    const [search, setSearch] = useState("");
    const [campaigns, setCampaigns] = useState<Campaign[]>([]);

    // Fetch campaigns from backend
    useEffect(() => {
        const fetchCampaigns = async () => {
            try {
                const res = await fetch("http://localhost:8000/api/campaigns/", {
                    method: "GET",
                    headers: { "Content-Type": "application/json" },
                });
                const data: Campaign[] = await res.json();
                setCampaigns(data);
            } catch (err) {
                console.error(err);
                throw new Error("Failed to fetch campaigns");
            }
        };

        fetchCampaigns();
    }, []); // no dependencies, fetch once on mount

    // Automatically select the newest campaign if none selected
    useEffect(() => {
        if (campaigns.length > 0 && !selectedCampaign) {
            const newestCampaign = campaigns.reduce((latest, current) =>
                new Date(current.last_seen) > new Date(latest.last_seen)
                    ? current
                    : latest
            );
            setSelectedCampaign(newestCampaign);
        }
    }, [campaigns, selectedCampaign, setSelectedCampaign]);

    const filteredCampaigns = useMemo(() => {
        return campaigns
            .filter((c) =>
                c.name.toLowerCase().includes(search.toLowerCase())
            )
            .sort(
                (a, b) =>
                    new Date(b.last_seen).getTime() -
                    new Date(a.last_seen).getTime()
            );
    }, [search, campaigns]);

    return (
        <Popover.Root>
            <Popover.Trigger asChild>
                <Button color="iris">
                    Choose a campaign...
                </Button>
            </Popover.Trigger>

            <Popover.Content
                side="bottom"
                align="start"
                className="z-50 w-64 mt-2 rounded-lg bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 shadow-lg p-2"
            >
                {/* Search input */}
                <input
                    type="text"
                    placeholder="Search campaign..."
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    className="w-full mb-2 px-3 py-2 text-sm rounded-md border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:outline-none"
                />

                <div className="max-h-91 overflow-y-auto">
                    {filteredCampaigns.map((campaign) => (
                        <div
                            key={campaign.id}
                            onClick={() => {
                                setSelectedCampaign(campaign);
                                setSearch("");
                            }}
                            className="px-3 py-2 text-sm rounded-md cursor-pointer text-gray-900 dark:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-700"
                        >
                            <div className="flex flex-col gap-1">
                                <span className="font-medium">{campaign.name}</span>
                                <span className="text-xs text-gray-500">
                                    Last seen{" "}
                                    {formatDistanceToNow(
                                        new Date(campaign.last_seen),
                                        { addSuffix: true }
                                    )}
                                </span>
                            </div>
                        </div>
                    ))}
                </div>
            </Popover.Content>
        </Popover.Root>
    );
};

export default CampaignDropdown;