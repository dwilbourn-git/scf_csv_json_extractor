# MongoDB / Document Database Structure Guide

This guide explains the different structure options for importing SCF data into MongoDB or other document databases.

## Available Export Formats

### 1. Relational-Style JSON (Default)
**Command:** `python main.py run --format json`

**Structure:** Separate files for each entity type, similar to relational database tables.

```
json_output/
├── SCF.json                           # 338 controls
├── SCF_Domains_Principles.json        # 34 domains
├── Assessment_Objectives.json         # 2,029 objectives
├── scf_relationships/                 # 5 files
│   ├── scf_to_domain.csv
│   ├── scf_to_evidence_request_list.json
│   └── ...
└── framework_relationships/           # 258 files
    ├── scf_to_nist_800_53_rev5.json
    ├── scf_to_iso_27001_v2022.json
    └── ...
```

**Pros:**
- Minimal data duplication
- Easy to update individual entities
- Familiar to SQL developers

**Cons:**
- Requires multiple queries or $lookup operations
- Complex client-side joins
- Slower read performance

**Best for:** Applications that frequently update individual entities or need minimal storage.

---

### 2. MongoDB-Optimized Structure (Recommended)
**Command:** `python export_mongodb.py`

**Structure:** Single file with fully embedded documents (9.5MB for 338 controls).

**Document Structure:**
```json
{
  "_id": "GOV-01",
  "control_id": "GOV-01",
  "control_number": "Cybersecurity & Data Protection Governance Program",
  "title": "Mechanisms exist to facilitate...",

  "domain": {
    "identifier": "GOV",
    "name": "Cybersecurity & Data Privacy Governance",
    "principle": "Execute a documented, risk-based program...",
    "principle_intent": "Organizations specify the development..."
  },

  "control_question": "Does the organization facilitate...",
  "relative_weight": "10",

  "solutions_by_business_size": {
    "micro_small": "...",
    "small": "...",
    "medium": "...",
    "large": "...",
    "enterprise": "..."
  },

  "pptdf_applicability": {
    "people": false,
    "process": true,
    "technology": false,
    "data": false,
    "facilities": false
  },

  "scf_core": {
    "esp_level_1_foundational": false,
    "esp_level_2_critical_infrastructure": false,
    "esp_level_3_advanced_threats": false,
    "ai_model_deployment": false,
    "ai_enabled_operations": false,
    "fundamentals": false,
    "mergers_acquisitions_divestitures": false,
    "community_derived": false
  },

  "conformity_validation_cadence": "Annual",

  "assessment_objectives": [
    {
      "ao_id": "GOV-01_A01",
      "objective": "...",
      "discussion": "..."
    }
  ],

  "scf_relationships": {
    "evidence_request_list_erl_id": ["ERL-001", "ERL-002"],
    "control_threat_summary": ["..."],
    "risk_threat_summary": ["..."]
  },

  "framework_mappings": {
    "nist_800_53_rev5": ["PM-1", "PM-2", "PM-3"],
    "iso_27001_v2022": ["5.1", "5.2"],
    "pci_dss_v4_0_1": ["12.1.1", "12.1.2"],
    "aicpa_tsc_2017_2022_used_for_soc_2": ["CC1.1", "CC1.2"],
    // ... 121 more frameworks
  }
}
```

**Pros:**
- **Single query** to get complete control information
- **Fast reads** - no joins required
- **Self-contained documents** - easy to work with in code
- **Optimized for MongoDB** - leverages document model strengths
- **Ready for GraphQL/REST APIs** - matches typical API response structure

**Cons:**
- Data duplication (domain info repeated across controls)
- Larger documents (~28KB average per control)
- Updates to domains require updating multiple controls

**Best for:**
- Read-heavy workloads (APIs, web apps)
- Applications that typically query individual controls
- GraphQL APIs
- Microservices architectures

**Performance Characteristics:**
- File size: 9.5MB (338 controls)
- Average document size: ~28KB
- Framework mappings per control: ~125 frameworks
- Assessment objectives per control: ~6 objectives

---

### 3. Hybrid Structure (Custom Implementation)
**Structure:** Mix of embedded and referenced data based on access patterns.

**Example:**
```json
{
  "_id": "GOV-01",
  "control_id": "GOV-01",
  "title": "...",

  // Embedded: Small, frequently accessed data
  "domain": {
    "identifier": "GOV",
    "name": "Cybersecurity & Data Privacy Governance"
  },

  // Embedded: Control-specific data
  "pptdf_applicability": { ... },
  "scf_core": { ... },

  // Referenced: Large or frequently changing data
  "domain_details_ref": "GOV",  // Reference to domains collection
  "assessment_objectives_ref": ["GOV-01_A01", "GOV-01_A02"],

  // Embedded: Framework mappings (if needed frequently)
  "framework_mappings": { ... }
}
```

**Pros:**
- Balance of performance and maintainability
- Reduces duplication for large/changing data
- Flexibility to optimize per use case

**Cons:**
- More complex to implement
- Requires careful design decisions
- May still need some $lookup operations

**Best for:** Applications with mixed read/write patterns or specific performance requirements.

---

## Import Instructions

### MongoDB Import

**Option 1: Using mongoimport (for relational-style)**
```bash
# Import main controls
mongoimport --db scf --collection controls --file json_output/SCF.json --jsonArray

# Import domains
mongoimport --db scf --collection domains --file json_output/SCF_Domains_Principles.json --jsonArray

# Import framework relationships
mongoimport --db scf --collection framework_mappings --file json_output/framework_relationships/scf_to_nist_800_53_rev5.json --jsonArray
```

**Option 2: Using mongoimport (for MongoDB-optimized)**
```bash
# Import embedded controls (single collection)
mongoimport --db scf --collection controls --file scf_mongodb.json --jsonArray
```

**Option 3: Using Python/PyMongo**
```python
from pymongo import MongoClient
import json

client = MongoClient('mongodb://localhost:27017/')
db = client['scf']

# Load and insert
with open('scf_mongodb.json', 'r', encoding='utf-8') as f:
    controls = json.load(f)
    db.controls.insert_many(controls)

# Create indexes for performance
db.controls.create_index('domain.identifier')
db.controls.create_index('framework_mappings.nist_800_53_rev5')
db.controls.create_index('scf_core.esp_level_1_foundational')
```

### DocumentDB / CosmosDB Import

Similar to MongoDB, but may need to adjust for specific API differences.

---

## Query Examples

### MongoDB-Optimized Structure

**Get a single control with all information:**
```javascript
db.controls.findOne({ _id: "GOV-01" })
```

**Find all controls in a domain:**
```javascript
db.controls.find({ "domain.identifier": "GOV" })
```

**Find controls mapped to a specific framework:**
```javascript
db.controls.find({ "framework_mappings.nist_800_53_rev5": { $exists: true } })
```

**Find controls by SCF CORE classification:**
```javascript
db.controls.find({ "scf_core.esp_level_1_foundational": true })
```

**Find controls with specific PPTDF applicability:**
```javascript
db.controls.find({
  "pptdf_applicability.technology": true,
  "pptdf_applicability.data": true
})
```

**Complex query: Find Level 1 controls mapped to NIST:**
```javascript
db.controls.find({
  "scf_core.esp_level_1_foundational": true,
  "framework_mappings.nist_800_53_rev5": { $exists: true }
},
{
  _id: 1,
  title: 1,
  "framework_mappings.nist_800_53_rev5": 1
})
```

### Relational-Style Structure (Requires $lookup)

**Get control with domain information:**
```javascript
db.controls.aggregate([
  { $match: { scf_id: "GOV-01" } },
  { $lookup: {
      from: "domains",
      localField: "domain_identifier",
      foreignField: "scf_identifier",
      as: "domain"
  }}
])
```

---

## Recommendations by Use Case

### Use MongoDB-Optimized (export_mongodb.py) if:
- ✅ Building a REST or GraphQL API
- ✅ Read-heavy workload (compliance dashboards, reporting)
- ✅ Need fast single-control lookups
- ✅ Working with serverless/microservices
- ✅ Want to leverage MongoDB's document model
- ✅ OK with 9.5MB data size for 338 controls

### Use Relational-Style JSON if:
- ✅ Need minimal data duplication
- ✅ Frequently update domains or frameworks independently
- ✅ Have complex update patterns
- ✅ Coming from SQL background
- ✅ Need absolute minimal storage
- ✅ OK with more complex queries

### Use Hybrid Structure if:
- ✅ Have specific performance requirements
- ✅ Need fine-grained control over embedding vs. referencing
- ✅ Have mixed read/write patterns
- ✅ Want to optimize for specific queries

---

## Performance Considerations

### MongoDB-Optimized Structure

**Advantages:**
- Single query retrieval: ~1-2ms
- No $lookup operations needed
- Document size: ~28KB average (well within 16MB BSON limit)
- Ideal for caching (Redis, etc.)

**Trade-offs:**
- Update propagation: Changing domain name requires updating multiple controls
- Storage: ~2.5x larger than relational (9.5MB vs ~4MB)
- Index size: Larger if indexing embedded fields

### Indexing Strategy

**Recommended indexes for MongoDB-Optimized:**
```javascript
// Primary lookups
db.controls.createIndex({ _id: 1 })  // Already exists
db.controls.createIndex({ "domain.identifier": 1 })

// Framework mapping queries
db.controls.createIndex({ "framework_mappings.nist_800_53_rev5": 1 })
db.controls.createIndex({ "framework_mappings.iso_27001_v2022": 1 })
db.controls.createIndex({ "framework_mappings.pci_dss_v4_0_1": 1 })

// SCF CORE classifications
db.controls.createIndex({ "scf_core.esp_level_1_foundational": 1 })
db.controls.createIndex({ "scf_core.esp_level_2_critical_infrastructure": 1 })

// PPTDF applicability
db.controls.createIndex({ "pptdf_applicability.technology": 1 })

// Text search
db.controls.createIndex({ title: "text", "domain.name": "text" })
```

---

## Conclusion

**For most applications, the MongoDB-Optimized structure (export_mongodb.py) is recommended** because:
1. It's designed for document databases
2. Provides the best query performance
3. Simplifies application code
4. Matches typical API response structures
5. Works well with modern frameworks (React, Vue, Angular)

The file size (9.5MB) and document size (~28KB) are reasonable for modern systems, and the performance benefits of embedded documents typically outweigh the storage cost.
