import re

with open("src/load_supabase.py", "r") as f:
    content = f.read()

old_str = """                JOIN dim_settlement dst ON dst.settlement_key = dstore.settlement_key
                WHERE ($1 IS NULL OR f.date_key            = $1)
                  AND ($2 IS NULL OR dstore.settlement_key = $2)
                  AND ($3 IS NULL OR f.category_key        = $3)
                  AND ($4 IS NULL OR dstore.company_key    = $4)
                  AND ($5 IS NULL OR f.store_key           = $5)
                  AND ($6 IS NULL OR dp.product_name ILIKE '%%' || $6 || '%%')
                  AND ($7 IS NULL OR COALESCE(
                        CASE WHEN f.promo_price IS NOT NULL AND f.promo_price > 0
                            THEN LEAST(f.retail_price, f.promo_price)
                            ELSE f.retail_price END,
                        f.retail_price) >= $7)
                  AND ($8 IS NULL OR COALESCE(
                        CASE WHEN f.promo_price IS NOT NULL AND f.promo_price > 0
                            THEN LEAST(f.retail_price, f.promo_price)
                            ELSE f.retail_price END,
                        f.retail_price) <= $8)
            ) inner_data
            GROUP BY %I %s
            ORDER BY %I
        ) g
    $q$, p_group_by_1, v_select_group2, p_group_by_1, v_groupby_extra, p_group_by_1);"""

new_str = """                JOIN dim_settlement dst ON dst.settlement_key = dstore.settlement_key
                WHERE 1=1
                %s
            ) inner_data
            GROUP BY %I %s
            ORDER BY %I
        ) g
    $q$, p_group_by_1, v_select_group2,
    
    (CASE WHEN p_date_key IS NOT NULL THEN ' AND f.date_key = $1 ' ELSE '' END) || 
    (CASE WHEN p_settlement_key IS NOT NULL THEN ' AND dstore.settlement_key = $2 ' ELSE '' END) || 
    (CASE WHEN p_category_key IS NOT NULL THEN ' AND f.category_key = $3 ' ELSE '' END) || 
    (CASE WHEN p_company_key IS NOT NULL THEN ' AND dstore.company_key = $4 ' ELSE '' END) || 
    (CASE WHEN p_store_key IS NOT NULL THEN ' AND f.store_key = $5 ' ELSE '' END) || 
    (CASE WHEN p_product_name IS NOT NULL THEN ' AND dp.product_name ILIKE ''%%'' || $6 || ''%%'' ' ELSE '' END) || 
    (CASE WHEN p_price_min IS NOT NULL THEN ' AND COALESCE(
                        CASE WHEN f.promo_price IS NOT NULL AND f.promo_price > 0
                            THEN LEAST(f.retail_price, f.promo_price)
                            ELSE f.retail_price END,
                        f.retail_price) >= $7 ' ELSE '' END) || 
    (CASE WHEN p_price_max IS NOT NULL THEN ' AND COALESCE(
                        CASE WHEN f.promo_price IS NOT NULL AND f.promo_price > 0
                            THEN LEAST(f.retail_price, f.promo_price)
                            ELSE f.retail_price END,
                        f.retail_price) <= $8 ' ELSE '' END),
    
    p_group_by_1, v_groupby_extra, p_group_by_1);"""

if old_str in content:
    with open("src/load_supabase.py", "w") as f:
        f.write(content.replace(old_str, new_str))
    print("Patched!")
else:
    print("Not found!")
