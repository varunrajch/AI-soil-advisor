# Guideline documents used for RAG

These PDFs ground the plan explanations. They do **not** set the doses in `engine.py`, which are still illustrative.

| File | What it is | Source |
|---|---|---|
| `icar_indian_farming_rice_zinc.pdf` | ICAR-IIWM, *Indian Farming* (May 2023): zinc fertilizer in rice, why, when and how | https://epubs.icar.org.in/index.php/IndFarm/article/download/134181/50124/361727 |
| `icar_indian_farming_groundnut_gypsum.pdf` | ICRISAT authors, ICAR *Indian Farming* (Apr 2024): gypsum improves groundnut pod yield | https://epubs.icar.org.in/index.php/IndFarm/article/download/110893/54313/409456 |
| `ap_soil_test_fertiliser_adoption_2017.pdf` | Ministry of Agriculture study: adoption of soil-test-based fertiliser doses in Andhra Pradesh (2016-17) | https://desagri.gov.in/wp-content/uploads/2024/03/2016-17-ADOPTION-OF-RECOMMENDED-DOSES-OF-FERTILISERS-ON-SOIL-TEST-BASIS-IN-ANDHRA.pdf |
| `aau_rice_zinc_factsheet.pdf` | Assam Agricultural University / APART rice fact sheet (zinc) | https://rkbassam.aau.ac.in/uploads/factsheets/pdf/6650539488d17.pdf |
| `uas_bangalore_technologies_2025.pdf` | UAS Bangalore: new technologies for the package of practices (2025, Karnataka) | https://www.uasbangalore.edu.in/wp-content/uploads/2025/06/technologies-E-2025.pdf |
| `icar_pop_10_crops.pdf` | ICAR action-taken report on GOBARdhan (2024): organic manure with recommended fertiliser doses | https://gobardhan.sbm.gov.in/whats-new/Updated%20PoP%20for%2010%20crops%20by%20ICAR.pdf |

To add more (for example ANGRAU's Vyavasaya Panchangam), drop the PDF in this folder and rebuild the index:

```bash
python3 -m backend.app.rag.ingest
```
