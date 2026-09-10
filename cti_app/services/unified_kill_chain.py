# based on https://iritt.medium.com/unified-kill-chain-soc-level-1-cyber-defence-frameworks-tryhackme-walkthrough-5ed762d5e8b9
# and https://www.unifiedkillchain.com/assets/The-Unified-Kill-Chain.pdf
from collections import OrderedDict

# OrderedDict ensures tactics follow the kill chain order
KILL_CHAIN_MAPPING_ORDERED = OrderedDict([
    # IN — Initial Foothold
    ("reconnaissance", "In"),
    ("resource-development", "In"),
    ("initial-access", "In"),
    ("persistence", "In"),
    ("defense-evasion", "In"),
    ("command-and-control", "In"),
    # Mobile-specific
    ("network-effects", "In"),
    ("remote-service-effects", "In"),

    # THROUGH — Network Propagation
    ("discovery", "Through"),
    ("privilege-escalation", "Through"),
    ("execution", "Through"),
    ("credential-access", "Through"),
    ("lateral-movement", "Through"),
    # ICS-specific
    ("evasion", "Through"),
    ("inhibit-response-function", "Through"),
    ("impair-process-control", "Through"),

    # OUT — Actions on Objectives
    ("collection", "Out"),
    ("exfiltration", "Out"),
    ("impact", "Out"),
])