// Lead Sorting Template for RKE FB to Onboard workflows
// Replace {SOURCE} with the actual source tag e.g. "Facebook - RKE Evan"

const b = $input.first().json.body || $input.first().json;
const full = b.full_name || ((b.first_name || "") + " " + (b.last_name || "")).trim();
const parts = full.split(" ");
const first_name = parts[0] || "";
const last_name = parts.slice(1).join(" ") || "";
const phone = b.phone || "";
const email = b.email || "";
const state = (b.location && b.location.state) || b.state || "";
const cdl = b["CDL-A License"] || b["Class A CDL"] || "";
const exp = b["OTR Experience"] || b["How many years of tractor trailer experience do you have?"] || "";
const flatbed = b["Flatbed Experience"] || b["Flatbed exp"] || "";
const sap = b["Are you on a SAP program?"] || b["Are you actively on a SAP program?"] || "";
const tags = b.tags || "";

// Parse experience months
const expLower = exp.toString().toLowerCase().replace(/\+/g, " ");
let expMonths = 0;
const mMatch = expLower.match(/(\d+)\s*month/);
const yMatch = expLower.match(/(\d+)\s*year/);
if (mMatch) expMonths = parseInt(mMatch[1]);
if (yMatch) expMonths += parseInt(yMatch[1]) * 12;
if (!mMatch && !yMatch) {
  const numMatch = exp.toString().trim().match(/(\d+)/);
  if (numMatch) expMonths = parseInt(numMatch[1]);
}

// Sorting logic - priority: Disqualified > SAP > Underexperienced > New Lead > Qualified
const cdlNo = cdl.toLowerCase().includes("no") || cdl === "";
const sapYes = sap.toLowerCase().includes("yes");
const underExp = expMonths < 20;
const noFlatbed = flatbed.toLowerCase().includes("no") || flatbed === "";

let stage = "Qualified";
if (cdlNo) stage = "Disqualified";
else if (sapYes) stage = "SAP";
else if (underExp) stage = "Underexperienced";
else if (noFlatbed) stage = "New Lead";

return [{ json: {
  first_name,
  last_name,
  phone,
  email,
  state,
  stage,
  tags,
  source: "{SOURCE}",
  notes: "CDL-A: " + (cdl || "N/A") + " | OTR Exp: " + (exp || "N/A") + " | Flatbed Exp: " + (flatbed || "N/A") + " | SAP: " + (sap || "N/A") + " | Stage: " + stage
} }];
