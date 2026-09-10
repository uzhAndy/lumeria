import React from "react";

const AboutPage: React.FC = () => {
    return (
        <div className="rounded p-10">

            {/* ONE single card only */}
            <div className="rounded-lg shadow p-10 bg-gray-50 space-y-6">

                {/* Title */}
                <h1 className="text-2xl font-bold text-gray-900">
                    About Lumeria
                </h1>

                {/* MITRE ATT&CK */}
                <div>
                    <h2 className="text-lg font-bold text-gray-900">
                        MITRE ATT&CK Framework
                    </h2>

                    <p className="text-sm text-gray-700 mt-2 text-justify hyphens-auto">
                        MITRE ATT&CK is a knowledge base that describes how cyber adversaries operate.
                        It is widely used in cybersecurity to support the collection, detection, analysis and defense against cyber threats.
                        It organizes attack information and provides a common language for describing attacker behavior.
                        It includes three domains: Enterprise (attacks on organizations and company systems), Mobile (attacks on smartphones and tablets) and Industrial Control Systems (attacks on systems that control critical infrastructure).
                        A central concept in MITRE ATT&CK is the grouping of attacker behavior into tactics and techniques.
                        Tactics describe the attacker’s goals, while techniques describe the methods used to achieve those goals.
                        MITRE ATT&CK also documents cyber campaigns.
                        These are groups of related attacks that occur over a short time period and share similar goals.
                        They may or may not be linked to a specific attacker group.
                        Campaigns help describe how attackers behave and support better understanding and prioritization of threats.
                    </p>
                </div>

                {/* Application Overview */}
                <div>
                    <h2 className="text-lg font-bold text-gray-900">
                        Application Overview
                    </h2>

                    <p className="text-sm text-gray-700 mt-2 text-justify hyphens-auto">
                        <strong>Lumeria</strong> is a platform for exploring cyber threat campaigns based on MITRE ATT&CK data. It transforms complex technical intelligence from MITRE ATT&CK into structured and more easily understandable insights, helping users with different backgrounds understand how attackers operate.
                        The platform consists of multiple widgets, all focused on the campaign currently selected by the user.
                    </p>

                    <ul className="text-sm text-gray-700 mt-4 space-y-2 list-disc list-outside pl-6 text-justify">
                        <li><strong>Threat Brief:</strong> The Threat Brief converts attack data into a step-by-step kill chain narrative. A chatbot explains each stage of the attack. Users can ask questions at any time about the displayed attack or general questions about MITRE ATT&CK. All responses are generated using a retrieval-augmented generation pipeline. This ensures that the responses are based on actual MITRE ATT&CK data, thereby improving their factual accuracy.</li>
                        <li><strong>Executive Summary:</strong> Overview of attacker behavior, potential impact and objective of the selected campaign.</li>
                        <li><strong>FAQs:</strong> Collection of AI-generated and user-defined questions about the campaign. The questions can be added and removed as needed.</li>
                        <li><strong>Visualizations:</strong> Multiple interactive charts show the campaign’s techniques, tactics, affected platforms and similar threat actor groups. The goal of these charts is to support exploration of the campaign data.</li>
                    </ul>
                </div>

            </div>
        </div>
    );
};

export default AboutPage;