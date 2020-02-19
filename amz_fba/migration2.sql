
update sale_order
set amz_order_type = 'ebay'
where id in (
select id
  from sale_order
where store_id in (1,3,4,5)
and amz_order_type is NULL)


update sale_order
set amz_order_type = 'normal'
where id in (
select id
  from sale_order
where store_id = 7
and amz_order_type is NULL)

update stock_picking
set amz_order_type = 'ebay'
where id in (
select id
  from stock_picking
where store_id in (1,3,4,5)
and amz_order_type is NULL)


update stock_picking
set amz_order_type = 'normal'
where id in (
select id
  from stock_picking
where store_id = 7
and amz_order_type is NULL)