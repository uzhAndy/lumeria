import React, { useEffect, useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { Badge, Button, Flex} from "@radix-ui/themes";
import { PlusIcon, TrashIcon } from "@radix-ui/react-icons";
import type {Campaign} from "../types/campaign.ts";
import type {Faq} from "../types/faq.ts";
import { useNavigate, useParams } from "react-router-dom";
import { useLocation } from "react-router-dom";


const FaqManagementPage: React.FC = () => {
    const [faqs, setFaqs] = useState<Faq[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const navigate = useNavigate();
    const { campaignId } = useParams<{ campaignId: string }>(); // used to find out which campaign is currently selected
    const location = useLocation();
    const passedCampaign = location.state?.campaign as Campaign | undefined;
    const [campaign, setCampaign] = useState<Campaign | null>(
        passedCampaign ?? null
    );

    const [question, setQuestion] = useState("");

    useEffect(() => {
        if (!campaignId){
            navigate("/dashboard")
            return;
        }

        let isMounted = true;

        const fetchData = async () => {
            setLoading(true);
            setError(null);

            try {
                //  Fetch campaign if not available to fix displayed campaign information loss on page reload
                if (!passedCampaign) {
                    const campaignRes = await fetch(
                        `http://localhost:8000/api/campaigns/${campaignId}/`
                    );
                    const campaignData: Campaign = await campaignRes.json();

                    if (isMounted) {
                        setCampaign(campaignData);
                    }
                }

                const faqRes = await fetch(
                    `http://localhost:8000/api/campaigns/${campaignId}/faqs/`
                );
                const faqData: Faq[] = await faqRes.json();

                if (isMounted) {
                    setFaqs(faqData);
                }

            } catch (err) {
                console.error("Fetch error:", err);
                if (isMounted) {
                    setError("Could not load data.");
                }
            } finally {
                if (isMounted) {
                    setLoading(false);
                }
            }
        };

        fetchData();

        return () => {
            isMounted = false;
        };
    }, [campaignId, navigate, passedCampaign]);

    const handleAddFaq = async () => {
        if (!campaignId || !question ) return;

        setLoading(true);
        setError(null);

        try {
            await fetch(
                `http://localhost:8000/api/campaigns/${campaignId}/faqs/`,
                {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ question }),
                }
            );

            setQuestion("");

            // re-fetch FAQs (same pattern)
            const res = await fetch(
                `http://localhost:8000/api/campaigns/${campaignId}/faqs/`,
                {
                    method: "GET",
                    headers: { "Content-Type": "application/json" },
                }
            );
            setFaqs(await res.json());
        } catch (err) {
            console.error("Add FAQ error:", err);
            setError("Could not add FAQ.");
        } finally {
            setLoading(false);
        }
    };

    const handleDeleteFaq = async (faqId: number) => {
        if (!campaignId) return;

        setLoading(true);
        setError(null);

        try {
            await fetch(
                `http://localhost:8000/api/campaigns/${campaignId}/faqs/${faqId}/`,
                { method: "DELETE" }
            );

            setFaqs((prev) => prev.filter((f) => f.id !== faqId));
        } catch (err) {
            console.error("Delete FAQ error:", err);
            setError("Could not delete FAQ.");
        } finally {
            setLoading(false);
        }
    };

    if (loading) {
        return <p className="p-10">Loading FAQs...</p>;
    }

    if (error) {
        return (
            <p className="p-10 text-red-600 font-bold">
                Error: {error}
            </p>
        );
    }

    return (
        <div className="flex flex-col h-full rounded p-10 space-y-6">
            <Flex justify="between" align="center" className="mb-6">
                {/* Header */}
                <div>
                <h2 className="text-2xl font-bold text-gray-900 text-left">
                    Manage FAQs for <em className="text-blue-700 font-semibold">{campaign?.name}</em>
                </h2>
                <p className="mt-1 text-sm text-gray-600">
                    Define the business questions that must always be answered when analyzing a certain campaign.
                    <br />
                    Some questions are automatically generated by default and can be edited or removed as needed.
                </p>
                </div>

                {/* Add FAQ Button & Dialog */}
                <Dialog.Root>
                    <Dialog.Trigger asChild>
                        <Button
                            size="3"
                        >
                            <PlusIcon className="w-5 h-5" /> Create a new campaign FAQ
                        </Button>
                    </Dialog.Trigger>

                    <Dialog.Portal>
                        <Dialog.Overlay className="fixed inset-0 bg-black/50 z-40" />
                        <Dialog.Content
                            className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-white p-6 rounded-lg shadow-xl max-w-md z-50"
                        >

                            <Dialog.Title className="text-xl font-semibold mb-2 text-gray-900">
                                New FAQ
                            </Dialog.Title>
                            <p className="text-gray-700 mb-4 text-sm">
                                Enter a question the company needs answered or that users frequently ask about this campaign.
                            </p>

                            <div className="flex flex-col gap-3">
                                <input
                                    type="text"
                                    placeholder="Question"
                                    value={question}
                                    onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                                        setQuestion(e.target.value)
                                    }
                                    className="w-full px-4 py-3 border border-gray-400 rounded-md text-gray-900 placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-600"
                                />

                                <div className="flex gap-2 justify-between mt-4">
                                    <Dialog.Close
                                        asChild
                                        onClick={() => setQuestion("")}
                                    >
                                        <button className="font-extrabold">
                                            Cancel
                                        </button>
                                    </Dialog.Close>

                                    <button
                                        onClick={handleAddFaq}
                                    >
                                        Save
                                    </button>
                                </div>
                            </div>
                        </Dialog.Content>
                    </Dialog.Portal>
                </Dialog.Root>
            </Flex>

            {faqs.length === 0 ? (
                <p className="font-semibold">No FAQs available for this campaign.</p>
            ) : (
                <div className="space-y-3">
                    {faqs.map((faq) => (
                        <div
                            key={faq.id}
                            className="rounded-lg shadow p-4 flex justify-between items-start bg-gray-50"
                        >
                            <div className="text-left mr-20">
                                {faq.is_ai_generated && (
                                    <Badge color="iris">
                                        <span className="font-extrabold">AI-generated</span>
                                    </Badge>
                                )}
                                <p className="mt-1.5"> <strong>{faq.question}</strong> </p>
                                <p className="text-sm text-left whitespace-pre-wrap mt-1">
                                    {faq.answer}
                                </p>
                            </div>

                            <Button
                                onClick={() => handleDeleteFaq(faq.id)}
                            >
                                <TrashIcon />
                                Delete Question
                            </Button>
                        </div>
                    ))}
                </div>
            )}
            <div className="flex items-start">
                <Button
                    size="4"
                    onClick={() => navigate("/dashboard", {
                        state: { selectedCampaign: campaign }
                    })}
                >
                    Back to Dashboard
                </Button>
            </div>
        </div>
    );
};

export default FaqManagementPage;
