import assert from "node:assert/strict";
import utils from "../extension-utils.js";

assert.equal(utils.roleSearchTerms("Product Designer"), "product manager");
assert.ok(utils.buildLinkedInPeopleSearchUrl("OpenAI", "Software Engineer").includes("linkedin.com/search/results/people"));
assert.equal(utils.normalizeLinkedInUrl("https://www.linkedin.com/in/test/?miniProfile=1"), "https://www.linkedin.com/in/test/");
assert.equal(utils.candidateRelevance({ title: "Recruiter at OpenAI" }, { companyName: "OpenAI" }), "company_match");
assert.equal(utils.hasSendCapacity({ remaining: 1 }), true);
assert.equal(utils.shouldKeepSendTabOpen("manual_required"), true);
