# Gold-answer primary-source audit

41 gold-check items; automatic re-derivation matches gold for 41; mismatches 0; errors 0. Raw payloads archived under `eval/review/gold_audit/<id>/`.
Automatic matching is a machine check, not human verification; the `Verified (human)` column of the review workbook records the latter.

| id | match | gold | audit value | evidence |
|---|---|---|---|---|
| why-NCT01910649 | True | "Regulatory approval was not obtained for drisapersen, hence BioMarin is stoppin | "Regulatory approval was not obtained for drisapersen, hence BioMarin is stoppin | overallStatus=TERMINATED; whyStopped='Regulatory approval was not obtained for drisapersen, hence BioMarin is stopping the development of all exon skipping oligonucleotides in DMD.' |
| why-NCT02945527 | True | "Low recruitment" | "Low recruitment" | overallStatus=TERMINATED; whyStopped='Low recruitment' |
| enrol-NCT07441525 | True | {"count": 27, "type": "ESTIMATED"} | {"count": 27, "type": "ESTIMATED"} | enrollmentInfo={'count': 27, 'type': 'ESTIMATED'} |
| enrol-NCT01658774 | True | {"count": 2377, "type": "ACTUAL"} | {"count": 2377, "type": "ACTUAL"} | enrollmentInfo={'count': 2377, 'type': 'ACTUAL'} |
| sap-NCT02572791 | True | true | true | largeDocs=[{'typeAbbrev': 'Prot_SAP', 'hasSap': True, 'filename': 'Prot_SAP_000.pdf'}] |
| sap-NCT03383614 | True | true | true | largeDocs=[{'typeAbbrev': 'Prot', 'hasSap': False, 'filename': 'Prot_000.pdf'}, {'typeAbbrev': 'SAP', 'hasSap': True, 'filename': 'SAP_001.pdf'}] |
| sites-NCT06982105 | True | 1 | 1 | 1 locations: Riley Hospital for Children, United States |
| sites-NCT06871007 | True | 2 | 2 | 2 locations: Dmitry Rogachev National Research Center, Russia; Pavlov University, RM Gorbacheva Research Institute, Russia |
| count-MONDO_0005498 | True | 2 | 2 | totalCount=2; e.g. NCT01940315, NCT01045694 |
| count-MONDO_0008889 | True | 2 | 2 | totalCount=2; e.g. NCT03056742, NCT06357663 |
| toptargets-MONDO_0010684 | True | ["VMA21", "HSPB8", "HNRNPA2B1", "GNE", "CLTA"] | ["VMA21", "HSPB8", "HNRNPA2B1", "GNE", "CLTA"] | VMA21 0.719; HSPB8 0.357; HNRNPA2B1 0.341; GNE 0.337; CLTA 0.333 |
| toptargets-MONDO_0010482 | True | ["ATP6AP2", "GLRB", "SPTBN4", "SCN8A", "GLRA1"] | ["ATP6AP2", "GLRB", "SPTBN4", "SCN8A", "GLRA1"] | ATP6AP2 0.518; GLRB 0.086; SPTBN4 0.083; SCN8A 0.082; GLRA1 0.077 |
| latedrugs-MONDO_0005445 | True | ["AMPHOTERICIN B", "MILTEFOSINE", "PAROMOMYCIN", "PAROMOMYCIN SULFATE", "SODIUM  | ["AMPHOTERICIN B", "MILTEFOSINE", "PAROMOMYCIN", "PAROMOMYCIN SULFATE", "SODIUM  | phase 3+ drugs: ['AMPHOTERICIN B', 'MILTEFOSINE', 'PAROMOMYCIN', 'PAROMOMYCIN SULFATE', 'SODIUM STIBOGLUCONATE'] |
| latedrugs-MONDO_0017287 | True | ["OBEXELIMAB", "RILZABRUTINIB"] | ["OBEXELIMAB", "RILZABRUTINIB"] | phase 3+ drugs: ['OBEXELIMAB', 'RILZABRUTINIB'] |
| generic-CHEMBL1483 | True | true | true | marketed ANDAs: 5 (e.g. ANDA213435, ANDA211034, ANDA211117) |
| generic-CHEMBL3707348 | True | false | false | no marketed ANDA |
| firstappr-CHEMBL1351 | True | 1989 | 1989 | CHEMBL1351 pref_name=CARBOPLATIN, first_approval=1989 |
| firstappr-CHEMBL221959 | True | 2012 | 2012 | CHEMBL221959 pref_name=TOFACITINIB, first_approval=2012 |
| targets-CHEMBL1201583 | True | ["VEGFA"] | ["VEGFA"] | Vascular endothelial growth factor A inhibitor -> ['VEGFA'] |
| targets-CHEMBL960 | True | ["DHODH"] | ["DHODH"] | Dihydroorotate dehydrogenase inhibitor -> ['DHODH'] |
| repurpose-MONDO_0005445 | True | ["AMPHOTERICIN B", "PAROMOMYCIN", "PAROMOMYCIN SULFATE"] | ["AMPHOTERICIN B", "PAROMOMYCIN", "PAROMOMYCIN SULFATE"] | AMPHOTERICIN B: marketed ANDAs: 4 (e.g. ANDA063206, ANDA214010, ANDA212514) / MILTEFOSINE: no Drugs@FDA record / PAROMOMYCIN: marketed ANDAs: 1 (e.g. ANDA065173) / PAROMOMYCIN SULFATE: marketed ANDAs: |
| repurpose-MONDO_0015908 | True | ["POSACONAZOLE"] | ["POSACONAZOLE"] | POSACONAZOLE: marketed ANDAs: 16 (e.g. ANDA216626, ANDA217119, ANDA218434) |
| nf-NCT96651360 | True | null | null | HTTP 404 for NCT96651360 |
| nf-CHEMBL99781738 | True | null | null | HTTP 404 for CHEMBL99781738 |
| rarity-178364 | True | true | true | Worldwide: None (Cases/families, Validated); Worldwide: <1 / 1 000 000 (Point prevalence, Validated) |
| rarity-342 | True | false | false | Turkey: >1 / 1000 (Point prevalence, Not yet validated); Armenia: >1 / 1000 (Point prevalence, Validated); Sweden: 1-9 / 100 000 (Point prevalence, Validated); Japan: 1-9 / 1 000 000 (Point prevalence |
| h1-MONDO_0009710 | True | 2 | 2 | 3 recruiting trials; countries: France, Italy |
| h1-MONDO_0013282 | True | 22 | 22 | 11 recruiting trials; countries: Australia, Austria, Belgium, Brazil, Canada, Czechia, Denmark, Finland, France, Georgia, Germany, Ireland, Italy, Netherlands, New Zealand, Poland, Portugal, Spain, Sw |
| h1-MONDO_0019004 | True | 10 | 10 | 25 recruiting trials; countries: Australia, Belgium, Canada, China, France, Germany, New Zealand, Puerto Rico, Saudi Arabia, United States |
| h2-MONDO_0005459 | True | [] | [] | EFLORNITHINE: no marketed ANDA / FEXINIDAZOLE: no marketed ANDA / MELARSOPROL: no Drugs@FDA record / NIFURTIMOX: no marketed ANDA |
| h2-MONDO_0005124 | True | [] | [] | CLOFAZIMINE: no marketed ANDA / DAPSONE: marketed ANDAs: 19 (e.g. ANDA213414, ANDA218335, ANDA203887); boxed warning on a current label: False / SULFOXONE SODIUM: no Drugs@FDA record |
| h2-MONDO_0008889 | True | [] | [] | BOTULINUM TOXIN TYPE A: no marketed ANDA / LETIBOTULINUMTOXINA: no marketed ANDA / ONABOTULINUMTOXINA: no marketed ANDA / SELEXIPAG: no marketed ANDA |
| h3-NCT01389687 | True | false | false | patient 1 months male; minimumAge=3 Months, maximumAge=68 Months, sex=ALL |
| h3-NCT06809777 | True | true | true | patient 38 years female; minimumAge=16 Years, maximumAge=60 Years, sex=ALL |
| h3-NCT01344798 | True | true | true | patient 16 years male; minimumAge=15 Years, maximumAge=None, sex=ALL |
| h4-CHEMBL820 | True | true | true | ChEMBL first_approval=1954; earliest ORIG-AP NDA in Drugs@FDA=1954 |
| h4-CHEMBL2096650 | True | false | false | ChEMBL first_approval=1992; earliest ORIG-AP NDA in Drugs@FDA=2011 |
| h4-CHEMBL1483 | True | true | true | ChEMBL first_approval=1996; earliest ORIG-AP NDA in Drugs@FDA=1996 |
| h5-MONDO_0010947 | True | ["DEUTIVACAFTOR", "VANZACAFTOR"] | ["DEUTIVACAFTOR", "VANZACAFTOR"] | top target CFTR; approved on target: ['DEUTIVACAFTOR', 'VANZACAFTOR']; tested for disease: 0 drugs |
| h5-MONDO_0007548 | True | ["BEREMAGENE GEPERPAVEC"] | ["BEREMAGENE GEPERPAVEC"] | top target COL7A1; approved on target: ['BEREMAGENE GEPERPAVEC']; tested for disease: 0 drugs |
| h5-MONDO_0017475 | True | ["COPANLISIB", "COPANLISIB HYDROCHLORIDE", "INAVOLISIB"] | ["COPANLISIB", "COPANLISIB HYDROCHLORIDE", "INAVOLISIB"] | top target PIK3CA; approved on target: ['COPANLISIB', 'COPANLISIB HYDROCHLORIDE', 'INAVOLISIB']; tested for disease: 0 drugs |
