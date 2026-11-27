# Edcons Foundry (ERPNext 16)

Shop-floor and lab logs for Edcons (MKS) Castings. Operators fill digital versions of the PR sheets they already
use. When a log is submitted, the app updates Work Orders, Job Cards, the Heat record, the Pattern record and
(optionally) stock, so data is entered only once.

## Install

```bash
bench get-app /path/to/edcons_foundry        # or a git URL
bench --site <site> install-app edcons_foundry
bench --site <site> migrate
bench build --app edcons_foundry
```

Install on a staging site first. This version has been syntax-checked, but it has not been run on a live bench.

## Where people start

| Who | Opens | Fills |
|---|---|---|
| Everyone | **/app/shop-floor** (Shop Floor hub, also in the apps screen as "Foundry") | Big stage tiles, today's numbers, own drafts |
| Melter | 1 · Melt → **Furnace Heat** | PR 2 (induction) / CI 1 (cupola): charge, temps, kWh, spectro |
| Mixer operator | 2 · Sand → **Sand Mix Log** | PR 32 batches, checked live against PR 46 limits |
| Moulding supervisor | 3 · Mould & Pour → **Production Entry** | PR 1 / CI 2 rows (moulder, party, item, heat), PR 4 pouring |
| Shot blast operator | 4 · Shot Blast → **Shot Blast Log** | PR 16 castings, PR 29 parts changed |
| Finishing supervisor | 5 · Finish → **Finishing Log** | PR 20 grinding, PR 19 casting weights |
| Inspector | 6 · Inspect → **Visual Inspection** | PR 21 defects per item |
| Lab | 7 · Load Test → **Load Test Report** | PR 33, prints the load test certificate |
| Quality | **Rejection Report** | Usually created automatically, fill in missing reasons |
| Anyone | **/app/heat-trace/<heat>** | Everything made from one heat, through to dispatch |

Every form shows a stage bar at the top (click any stage to jump to it), a **Next step** menu after submit that
copies the rows into the next log, and a **Trace heat** button.

## What happens automatically

| On submit of | The app does |
|---|---|
| Furnace Heat | Lining heat no. counted on the Furnace; CE %, kWh/t, cost per kg calculated; optional Material Issue of the charge |
| Production Entry | Job Cards for the mapped operations get the quantity; Heat No. written on Work Order and Job Card; Heat yield and Pattern shots updated; draft Rejection Report for rejected pieces; optional Material Receipt of return metal |
| Shot Blast Log | Shot blast / knockout Job Cards updated; draft Rejection Report |
| Finishing Log | Average weight from the PR 19 readings, Over/Underweight flag; fettling Job Cards; draft Rejection Report |
| Visual Inspection | Inspection Job Card (good qty); draft Rejection Report with one row per defect; draft Manufacture Stock Entry per Work Order for the OK pieces, for the storekeeper to submit |
| Rejection Report | Heat yield updated; optional Material Receipt of rejected castings into the return metal yard |
| Cancel of any log | Its Job Card quantity is removed (draft Job Cards), its stock entries are cancelled, its draft Rejection Report is deleted |

A posting that fails (no Job Card, Work Order closed, missing warehouse) never stops the operator. It is written
to **Posting Status** on the document and shown in orange; a supervisor fixes the cause and presses
**Retry ERP Posting**.

## Setup checklist

1. **Foundry Settings**: company, return metal item, warehouses, switch the stock postings on when ready.
2. **Operation Map** (in Foundry Settings) is filled on install for operations named Melting, Sand Mixing,
   Moulding, Pouring, Knockout, Shot Blasting, Fettling, Grinding, Inspection. Adjust it to your BOM routing.
   The log mapped to an operation completes that operation's Job Card, so map every operation in the routing,
   in routing order, or ERPNext will refuse a later operation before an earlier one is complete.
3. **Workstations**: set Production Capacity above 1 (for example 50) on each foundry workstation. Several logs
   are posted in the same minute, and with capacity 1 ERPNext reports overlapping time logs.
4. **Work Orders** should use "Transfer Material Against: Work Order" (not Job Card).
5. **Items**: fill the new Foundry section (book weight, grade, pattern). Book weight drives every kg figure.
6. **Furnaces**: create the induction furnace(s) and the cupola, with melt type DI or CI.
7. **Roles**: Foundry Operator (fills logs), Foundry Supervisor (submits), Lab Technician, Quality Manager,
   Plant Head (read). Assign them to users.

## Still to confirm with the client

- Which sand limits govern, PR 46 (seeded) or PR 32. Edit them in Foundry Settings.
- What "ladle capacity" means on PR 47, and what "top/bottom" means on PR 3.
- Whether workers are paid per piece (PR 20); a piece-rate payroll link is not built.
- That "FAR" means the weight of castings cast in a shift.

## Not in this version

PR 17 / PR 18 stage-stock reports, PR 8 order position report, maintenance logs (checklists, breakdowns, meter
readings), labour chart, and costing of the heat into the casting valuation.
"# EDCONS" 
