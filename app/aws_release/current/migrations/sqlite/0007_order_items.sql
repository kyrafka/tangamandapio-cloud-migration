-- 0007: conservar líneas SKU/cantidad en los pedidos generados para WMS.
ALTER TABLE orders ADD COLUMN items_json TEXT NOT NULL DEFAULT '[]';
