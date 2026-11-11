# Getting Started with Merlino

Merlino is a free Microsoft Excel Add-in for Cyber Threat Intelligence professionals. This guide gets you up and running in 5 minutes.

## Installation

Merlino is distributed through the **Microsoft Marketplace** and installed from
inside Excel.

1. Open Microsoft Excel.
2. Open the add-ins section from the ribbon and choose the **Microsoft
   Marketplace / Store**. Exact labels vary by Excel release.
3. Search for **Merlino**, confirm the publisher is **X3M.AI LTD**, then select
   **Add**.
4. On first use, accept the X3M.AI Terms of Use.

Official listing:
<https://marketplace.microsoft.com/en-us/product/wa200010289>

If Merlino does not appear or cannot be added, check that your Excel version
supports add-ins and that your organisation allows the Microsoft Marketplace;
the Store can be disabled by tenant policy. Contact
<support@x3m.ai> or [Contact us](https://x3m.ai/en/contact/) for help. Do not use
a manual manifest sideload or a BAT installer as a customer workaround.

After installation, the **Merlino** ribbon tab appears in Excel.

## First Steps

1. Click **Templates** in the Merlino ribbon and load the **Enterprise** template
2. Click **Sources** and import **Techniques**, **Groups**, **Software**, and **Campaigns**
3. Go to the **Groups** sheet and set `Pick = TRUE` on the threat groups relevant to your organization
4. Open **Runbooks** and run **Include Picks in Catalogue**
5. Run **Update Core** + **Smart View** to generate your coverage heatmap
6. Explore the **Main Coverage** sheet -- your prioritized ATT&CK matrix

## Learn More

For a complete walkthrough with six APT groups (APT28, APT29, APT33, APT39, APT42, MuddyWater), see the full **User Guide -- Lab 01: Create Organization Threat Profile**.

## Get Help

- **[Community Discussions](https://github.com/x3m-ai/Camelot/discussions)** -- Ask questions, get answers
- **[Troubleshooting](https://github.com/x3m-ai/Camelot/discussions/categories/troubleshooting)** -- Report issues

## Requirements

- Microsoft Excel (Microsoft 365, Excel 2021, or Excel Online)
- Windows 10/11 or macOS (for Desktop)
- Any modern browser (for Excel Online)
- Internet connection (for data imports and AI features)
