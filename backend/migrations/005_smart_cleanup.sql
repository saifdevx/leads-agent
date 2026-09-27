-- Remove historical empty lead-list shells left behind by deleted/import-failed data.
-- Running searches are preserved.
DELETE FROM lead_lists
WHERE status <> 'searching'
  AND NOT EXISTS (
      SELECT 1
      FROM leads
      WHERE leads.user_id = lead_lists.user_id
        AND leads.list_id = lead_lists.id
  );
