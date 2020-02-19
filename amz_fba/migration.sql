update sale_order set amz_order_type = 'fbm'
where id in
(select o.id from sale_order o
left join sale_store s
on o.store_id = s.id
where o.is_fbm_prime = True
and s.site = 'amz')

update sale_order set amz_order_type = 'normal'
where id in
(select o.id from sale_order o
left join sale_store s
on o.store_id = s.id
where (o.is_fbm_prime = false or o.is_fbm_prime is null)
and s.site = 'amz' order by o.id)

update sale_order set amz_order_type = 'ebay'
where id in
(select o.id from sale_order o
left join sale_store s
on o.store_id = s.id
where s.site = 'ebay')

-- same for Pickings
update stock_picking set amz_order_type = 'fbm'
where id in
(select p.id from stock_picking  p
left join sale_order o
on p.sale_id = o.id
left join sale_store s
on o.store_id = s.id
where p.is_fbm_prime = True
and s.site = 'amz')

update stock_picking set amz_order_type = 'normal'
where id in
(select p.id from stock_picking  p
left join sale_order o
on p.sale_id = o.id
left join sale_store s
on o.store_id = s.id
where (o.is_fbm_prime = false or o.is_fbm_prime is null)
and s.site = 'amz')

update stock_picking set amz_order_type = 'ebay'
where id in
(select p.id from stock_picking  p
left join sale_order o
on p.sale_id = o.id
left join sale_store s
on o.store_id = s.id
where s.site = 'ebay')
