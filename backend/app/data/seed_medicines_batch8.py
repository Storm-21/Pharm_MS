"""
Extended medicine reference data - batch 8.

Fills classes still absent after batch 7: dermatology (acne, psoriasis,
scabies, pediculosis, dermatophyte beyond the clotrimazole line), haematinics
beyond the iron+folic acid line, ophthalmic and otic preparations, and the
paediatric pain/fever strengths a counter is asked for daily.

Same contract as every batch: published figures only, None where a figure is
not reliably published, and test_catalogue.py holds this file to the same
guarantees as the others.
"""


def _med(name, generic, therapeutic_class, pharmacological_class, use_case,
         **kw):
    """Build one medicine record with the defaults the other batches use."""
    return {
        "name": name,
        "generic_name": generic,
        "brand_name": kw.get("brand", name.split()[0]),
        "manufacturer": kw.get("manufacturer",
                               "Various - multiple licensed manufacturers"),
        "manufacturer_country": "India",
        "manufacturer_site": kw.get("site", "India"),
        "manufacturer_licence_no": kw.get("licence", "Multiple - see the pack"),
        "marketed_by": kw.get("marketed_by", "Various"),
        "country_origin": "India",
        "salt_composition": kw.get("composition", name),
        "molecular_formula": kw.get("formula"),
        "chemical_formula_weight": kw.get("weight"),
        "strength": kw.get("strength", name.split()[-1]),
        "form": kw.get("form", "tablet"),
        "route_of_administration": kw.get("route", "Oral"),
        "therapeutic_class": therapeutic_class,
        "pharmacological_class": pharmacological_class,
        "use_case": use_case,
        "mechanism_of_action": kw.get("moa"),
        "side_effects": kw.get("side_effects"),
        "contraindications": kw.get("contra"),
        "warnings": kw.get("warnings"),
        "drug_interactions": kw.get("interactions"),
        "pregnancy_category": kw.get("pregnancy"),
        "half_life": kw.get("half_life"),
        "storage_temp": kw.get(
            "storage", "Store below 30C, protected from light and moisture"),
        "max_daily_dose": kw.get("max_dose"),
        "cost_price": kw.get("cost", 0.0),
        "selling_price": kw.get("price", 0.0),
        "requires_prescription": kw.get("rx", True),
        "schedule_classification": kw.get(
            "schedule", "Schedule H - prescription required"),
    }


BATCH8_MEDICINES = [

    # =================================================================== #
    # DERMATOLOGY - acne, psoriasis, scabies, pediculosis, dermatophyte
    # =================================================================== #

    _med(
        "Adapalene 0.1% Gel", "Adapalene",
        "Dermatological - topical retinoid for acne",
        "Retinoid; modulates follicular epithelial differentiation",
        "Acne vulgaris, comedonal and inflammatory lesions of face and trunk",
        strength="0.1%", form="gel", route="Topical", brand="Deriva",
        half_life="Negligible systemic absorption",
        moa="Binds retinoic acid receptor subtypes and normalises the desquamation of follicular epithelium, so comedones stop forming. Unlike tretinoin it is chemically stable in light and markedly less irritating, which is why it is the tolerated first choice.",
        side_effects="Local erythema, scaling, burning, dryness - worst in the first weeks.",
        contra="Hypersensitivity; avoid in eczematous or sunburned skin.",
        warnings="APPLY A THIN LAYER AT NIGHT ONLY, to clean dry skin, pea-sized for the whole face. Expect a purging flare of small papules in weeks 2-4 - warn or the patient abandons a working treatment. Use a sunscreen daily; retinoids thin the stratum corneum. Pregnancy: avoid, evidence is limited even though absorption is negligible.",
        interactions="Avoid abrasive cleansers and astringents in the same routine; do not combine with benzoyl peroxide in one application (use morning/evening).",
        pregnancy="C - topical use generally avoided in pregnancy",
        max_dose="Once daily topical",
        cost=95.0, price=225.0),

    _med(
        "Tretinoin 0.025% Cream", "Tretinoin",
        "Dermatological - topical retinoid",
        "Retinoid; normalises follicular keratinisation",
        "Acne vulgaris, photoaging, hyperkeratotic disorders",
        strength="0.025%", form="cream", route="Topical", brand="Retino-A",
        half_life="Negligible systemic absorption",
        moa="The all-trans retinoic acid receptor agonist that loosens existing comedones and prevents new ones by speeding follicular epithelial turnover. Adapalene is the better tolerated analogue; this remains the stronger option for refractory comedonal acne.",
        side_effects="Peeling, redness, stinging, photosensitivity - markedly stronger than adapalene.",
        contra="Pregnancy. Personal or family history of cutaneous epithelioma. Eczema, sunburn.",
        warnings="NIGHT USE ONLY with a pea-sized amount for the face. The treatment flare is real and expected in weeks 2-4. AVOID ON THE SAME NIGHT AS BENZOYL PEROXIDE - it degrades tretinoin chemically. Daily sunscreen is not optional. Pregnancy is a hard stop: systemic retinoids are teratogens and this is not prescribed casually at a counter.",
        interactions="Do not layer with benzoyl peroxide, salicylic acid or alcohol toners at the same application.",
        pregnancy="X - contraindicated",
        max_dose="Once daily topical",
        cost=48.0, price=110.0),

    _med(
        "Benzoyl Peroxide 2.5% Gel", "Benzoyl peroxide",
        "Dermatological - topical antibacterial for acne",
        "Oxidising agent; keratolytic and antibacterial",
        "Mild to moderate inflammatory acne; in combination for resistant acne",
        strength="2.5%", form="gel", route="Topical", brand="Benzac AC",
        half_life="Topical - no meaningful half-life",
        moa="Releases free oxygen radicals that are bactericidal to Cutibacterium acnes. Because the organism cannot develop resistance to oxidation it is the anchor of every durable acne regimen, and it is why topical antibiotic monotherapy is avoided.",
        side_effects="Dryness, peeling, burning; bleaches hair and coloured fabric.",
        contra="Known hypersensitivity; severe erythema on first application.",
        warnings="START 2.5% NOT 5% - the lower strength works as well with a third of the irritation, so the higher strength buys nothing. Apply for 15 minutes then wash off for the first week, building tolerance. IT BLEACHES PILLOWS, TOWELS AND CLOTHES - the commonest complaint and preventable by warning. Wash hands after applying.",
        interactions="Do not apply concurrently with tretinoin (same night).",
        pregnancy="C - topical, generally considered acceptable",
        max_dose="Once to twice daily topical",
        cost=62.0, price=145.0),

    _med(
        "Clindamycin 1% + Benzoyl Peroxide 3.75% Gel", "Clindamycin phosphate + Benzoyl peroxide",
        "Dermatological - topical antibiotic combination",
        "Lincosamide antibiotic plus oxidising agent",
        "Moderate inflammatory acne vulgaris when monotherapy is insufficient",
        strength="1% + 3.75%", form="gel", route="Topical", brand="Clinsol-BP",
        half_life="Negligible systemic absorption",
        moa="Clindamycin inhibits bacterial protein synthesis at the 50S ribosomal subunit; benzoyl peroxide supplies the oxidative kill so that C. acnes cannot develop resistance to the antibiotic alone. Fixed combination exists to make the pairing automatic rather than optional.",
        side_effects="Dryness, erythema, peeling, occasional diarrhoea if large areas are treated (absorbed clindamycin).",
        contra="History of regional enteritis, ulcerative colitis or antibiotic-associated colitis.",
        warnings="THIN LAYER TWICE DAILY on cleansed skin. If diarrhoea occurs, STOP AND REPORT - systemic absorption of clindamycin from large treated areas can cause pseudomembranous colitis even from a gel. Bleaches fabrics as with benzoyl peroxide alone. Not for use with a topical retinoid at the same time of day.",
        interactions="May potentiate neuromuscular blockers; avoid with erythromycin topicals.",
        pregnancy="B - considered acceptable",
        max_dose="Twice daily topical",
        cost=118.0, price=265.0),

    _med(
        "Tacrolimus 0.03% Ointment", "Tacrolimus",
        "Dermatological - topical calcineurin inhibitor",
        "Immunomodulator; calcineurin inhibition in T-lymphocytes",
        "Atopic dermatitis unresponsive to topical steroids, especially face, neck, flexures and genitals",
        strength="0.03%", form="ointment", route="Topical", brand="Tacroz Forte",
        formula="C44H69NO12", weight="804.02 g/mol",
        half_life="Systemic absorption negligible",
        moa="Blocks calcineurin, preventing NFAT activation and interleukin-2 transcription, so T-cell driven inflammation of atopic skin is switched off without thinning the dermis - the property that makes it the correct choice for skin where steroids cause atrophy.",
        side_effects="Transient burning and stinging on application (most patients, first week); rarely folliculitis, herpes simplex reactivation.",
        contra="Immunosuppressed patients; hypersensitivity; not for infected eczema without treating the infection.",
        warnings="FOR SKIN WHERE STEROIDS CAUSE ATROPHY - face, eyelids, neck, folds. The burning on the first applications is expected and diminishes; explain this or the ointment is abandoned on day one. Apply a thin layer twice daily. Not recommended under 2 years of age. Do not occlude or cover. Avoid excessive sun exposure.",
        interactions="Systemic absorption is minimal; avoid phototherapy concurrently.",
        pregnancy="C - topical, use only if clearly needed",
        max_dose="Twice daily topical",
        cost=285.0, price=620.0),

    _med(
        "Permethrin 5% Cream", "Permethrin",
        "Dermatological - pediculicide and scabicide",
        "Synthetic pyrethroid; neurotoxic to arthropods",
        "Scabies infestation; head lice",
        strength="5%", form="cream", route="Topical", brand="Permite",
        half_life="Negligible systemic absorption",
        moa="Disrupts voltage-gated sodium channels in arthropod nerve membranes, producing paralysis and death of the mite and louse. It is the first-line scabicide because ovicidal activity plus a favourable safety profile outperform older lindane-based products.",
        side_effects="Transient burning, stinging, tingling, erythema, numbness - often mirrors the infestation itself.",
        contra="Hypersensitivity to pyrethroids or chrysanthemums.",
        warnings="APPLY TO THE WHOLE BODY FROM THE NECK DOWN, INCLUDING UNDER THE NAILS, behind the ears and in skin folds - missing the webs of the fingers and the umbilicus is why treatment appears to fail. Leave 8-14 hours (overnight), then wash off. ALL HOUSEHOLD MEMBERS ARE TREATED THE SAME NIGHT; close contacts may be infested without symptoms. Wash clothing and bedding at 60C or seal for 72 hours. Repeat after 7 days if mites are still evident. In infants apply to the scalp and face also.",
        interactions="None of clinical significance.",
        pregnancy="B - first line in pregnancy for scabies",
        max_dose="Two applications one week apart",
        cost=98.0, price=210.0),

    _med(
        "Urea 10% Cream", "Urea",
        "Dermatological - emollient and keratolytic",
        "Humectant and keratolytic",
        "Xerosis, ichthyosis, cracked heels, hyperkeratosis; adjunct in eczema",
        strength="10%", form="cream", route="Topical", brand="Urasil",
        half_life="Topical - no meaningful half-life",
        moa="Breaks hydrogen bonds in the stratum corneum so water is drawn in and held, softening scale and restoring barrier function - the mechanism behind every winter-itch and cracked-heel remedy that actually works.",
        side_effects="Transient stinging on fissured skin.",
        contra="Hypersensitivity; not on acutely inflamed or weeping skin.",
        warnings="APPLY TWICE DAILY, ideally after bathing while the skin is still damp. Higher strengths (20-40%) are for gross hyperkeratosis; 10% is the maintenance strength. If the skin cracks bleed, a barrier dressing and review beat more urea. Safe in pregnancy and on children.",
        interactions="None of clinical significance.",
        pregnancy="Not applicable - no systemic absorption",
        max_dose="Twice daily topical",
        cost=45.0, price=98.0),

    _med(
        "Clobetasol Propionate 0.05% Ointment", "Clobetasol propionate",
        "Dermatological - very potent topical corticosteroid",
        "Glucocorticoid; anti-inflammatory and immunosuppressive",
        "Severe psoriasis, lichen planus, discoid lupus, resistant dermatoses - short courses only",
        strength="0.05%", form="ointment", route="Topical", brand="Propysal NF",
        half_life="Systemic absorption possible with prolonged use",
        moa="A class I (very potent) corticosteroid: vasoconstriction, suppression of inflammatory mediator release and inhibition of fibroblast and keratinocyte proliferation. Potency this high is exactly why duration must be bounded.",
        side_effects="Skin atrophy, striae, telangiectasia, hypopigmentation, perioral dermatitis, rebound on withdrawal.",
        contra="Untreated skin infection; rosacea; perioral dermatitis; acne; use on the face is generally contraindicated.",
        warnings="MAXIMUM 14 DAYS OF CONTINUOUS USE, and no more than 25-30 g a week, because atrophy and striae are permanent. NEVER ON THE FACE, genitals, or skin folds without specialist direction - those sites atrophy fastest. Do not stop abruptly after prolonged use; taper with a milder steroid to avoid rebound. In psoriasis, transition to an emollient and a vitamin D analogue for maintenance.",
        interactions="None topical of note.",
        pregnancy="C - avoid prolonged or large-area use",
        max_dose="50 g/week, max 4 weeks",
        cost=88.0, price=195.0),
]

BATCH8_GUIDES = [
    {"medicine_name": 'Adapalene 0.1% Gel', "age_group": '18+',
     "dosage_amount": 1, "dosage_unit": 'application',
     "frequency": "At bedtime", "duration_days": 90,
     "indication": 'Acne vulgaris',
     "special_notes": 'Pea-sized amount for the entire face, on clean dry skin, at night. Expect a purge in weeks 2-4 and a visible result only from week 8 - the abandonment point is week 3, so set the expectation on day one. Daily sunscreen is part of the treatment, not an optional extra. Elderly: same, but drier skin may need an added non-comedogenic moisturiser.'},
    {"medicine_name": 'Tretinoin 0.025% Cream', "age_group": '18+',
     "dosage_amount": 1, "dosage_unit": 'application',
     "frequency": "At bedtime", "duration_days": 90,
     "indication": 'Acne vulgaris, photoaging',
     "special_notes": 'Contraindicated in pregnancy - ask directly. Start alternate nights for the first two weeks to build tolerance. Never on the same night as benzoyl peroxide. Elderly: same precautions, more fragile skin.'},
    {"medicine_name": 'Benzoyl Peroxide 2.5% Gel', "age_group": '12-18',
     "dosage_amount": 1, "dosage_unit": 'application',
     "frequency": "Once daily, building to twice daily", "duration_days": 90,
     "indication": 'Mild to moderate inflammatory acne',
     "special_notes": 'Start with a 15-minute contact then wash off, increasing over a week. Bleaches fabric - warn. 2.5% outperforms nothing at 5% except irritation, so resist requests for a stronger tube. Elderly: not applicable, this is an adolescent/adult indication.'},
    {"medicine_name": 'Clindamycin 1% + Benzoyl Peroxide 3.75% Gel', "age_group": '18+',
     "dosage_amount": 1, "dosage_unit": 'application',
     "frequency": "Twice daily", "duration_days": 60,
     "indication": 'Moderate inflammatory acne',
     "special_notes": 'Stop and review immediately if diarrhoea develops. Do not combine with a topical retinoid at the same application. Bleaches fabric. Elderly: generally unnecessary - this is an adult-acne line.'},
    {"medicine_name": 'Tacrolimus 0.03% Ointment', "age_group": '2-6',
     "dosage_amount": 1, "dosage_unit": 'application',
     "frequency": "Twice daily", "duration_days": 30,
     "indication": 'Atopic dermatitis on face and flexures',
     "special_notes": 'Burning on the first applications is expected and reduces. Not under 2 years. Not on infected skin. Steroid-sparing maintenance can follow once control is achieved. Elderly: same, with closer skin surveillance.'},
    {"medicine_name": 'Permethrin 5% Cream', "age_group": '18+',
     "dosage_amount": 1, "dosage_unit": 'application',
     "frequency": "Overnight, repeat in 7 days", "duration_days": 1,
     "indication": 'Scabies infestation',
     "special_notes": 'THE WHOLE HOUSEHOLD, THE SAME NIGHT, is the single rule that decides whether treatment works. Include under the nails, web spaces, umbilicus, behind ears, genitals. Leave 8-14 hours, wash off. Wash or bag bedding and clothing. Elderly: often crusted scabies - needs medical review and a higher index of suspicion.'},
    {"medicine_name": 'Urea 10% Cream', "age_group": '18+',
     "dosage_amount": 1, "dosage_unit": 'application',
     "frequency": "Twice daily", "duration_days": 30,
     "indication": 'Xerosis, cracked heels',
     "special_notes": 'Apply on damp skin after bathing. Safe indefinitely; review only if fissures bleed. Elderly: the main user group - dry skin increases with age.'},
    {"medicine_name": 'Clobetasol Propionate 0.05% Ointment', "age_group": '18+',
     "dosage_amount": 1, "dosage_unit": 'application',
     "frequency": "Twice daily", "duration_days": 14,
     "indication": 'Severe plaque psoriasis, lichen planus, resistant dermatosis',
     "special_notes": 'MAXIMUM 2 WEEKS. Never the face or genitals. Under 25-30 g/week. Taper to a milder steroid or a vitamin D analogue rather than stopping dead. Elderly: thinner skin atrophies sooner - halve the duration and review at a week.'},
]
