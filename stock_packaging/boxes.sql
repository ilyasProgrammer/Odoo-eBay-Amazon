--Singles
INSERT INTO box_line (product_id, box_id, qty, comment)
select ppt.id, pp.id, sum(1), string_agg(ssp.name, ', ')
from stock_picking_packaging_line BOXLINE
LEFT JOIN product_product PP ON BOXLINE.packaging_product_id = PP.id
left join stock_picking ssp on BOXLINE.picking_id = ssp.id
left join stock_move sm on ssp.id = sm.picking_id
left join product_product ppp on sm.product_id = ppp.id
left join product_template ppt on ppp.product_tmpl_id = ppt.id
where   pp.id is not null
and BOXLINE.picking_id in (select id from (select sp.id id , sum(1) s
                                           from stock_picking_packaging_line sppl
                                           inner join stock_picking sp on sppl.picking_id = sp.id
                                           inner join stock_move sm on sm.picking_id = sp.id
                                           group by sp.id) a
                           where a.s = 1)
group by ppt.id, pp.id;


--Kits
INSERT INTO box_line (product_id, box_id, qty, comment)
SELECT pt.id produc_tmpl, pac.packaging_product_id, sum(1), string_agg(sp.name, ',')
FROM sale_order_line_kit solk
LEFT JOIN stock_picking sp ON solk.sale_order_id = sp.sale_id
inner JOIN stock_picking_packaging_line pac ON sp.id = pac.picking_id
LEFT JOIN product_product pp on solk.product_id = pp.id
LEFT JOIN product_template pt on pp.product_tmpl_id = pt.id
where sp.state = 'done' and sp.picking_type_id = 4
GROUP BY pt.id, pac.packaging_product_id
