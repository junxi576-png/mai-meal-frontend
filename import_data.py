import csv
from neo4j import GraphDatabase

# ================= 配置 Neo4j 连接 =================
URI = "neo4j+s://33f63140.databases.neo4j.io"
AUTH = ("33f63140", "j7HX3LORTgUjxT_RKPO9XRqW97UVeoSYVomoBjg-oGs")
# ===================================================

def safe_float(val, default=0.0):
    if not val:
        return default
    try:
        return float(val.strip())
    except (ValueError, TypeError):
        return default

def reset_and_import(ingredients_file, recipes_file, cooking_file="cooking_methods.csv", seasoning_file="seasoning_profiles.csv"):
    
    # ---------------- 1. 核心 Cypher 查询语句定义 ----------------

    clear_query = "MATCH (n) DETACH DELETE n"

    # 查询：导入基础食材 (包含微量元素)
    import_ingredient_query = """
    MERGE (i:Ingredient {id: $item_id})
    SET i.name_cn = $name_cn,
        i.name_en = $name_en,
        i.is_halal = $is_halal,
        i.is_vegan = $is_vegan,
        i.has_allium = $has_allium,
        i.gi_level = $gi_level,
        i.constraint_type = $constraint_type,
        i.price_tier = $price_tier,
        i.kcal = $energy_kcal,
        i.p = $protein_g,
        i.f = $fat_g,
        i.c = $carb_g,
        i.fiber_g = $fiber_g,     
        i.sodium_mg = $sodium_mg, 
        i.sugar_g = $sugar_g,
        // 👇 新增的三项微量元素 👇
        i.potassium_mg = $potassium_mg,
        i.phosphorus_mg = $phosphorus_mg,
        i.purine_mg = $purine_mg    

    MERGE (c:Category {name: $category})
    MERGE (sc:SubCategory {name: $sub_category})
    
    MERGE (sc)-[:UNDER_CATEGORY]->(c)
    MERGE (i)-[:BELONGS_TO]->(sc)
    """

    # 查询：AI 智能过敏原推理网络
    allergen_queries = [
        "MATCH (i:Ingredient) WHERE i.name_cn CONTAINS '花生' OR i.name_en CONTAINS 'peanut' MERGE (a:Allergen {name_cn: '花生', name_en: 'Peanut'}) MERGE (i)-[:CONTAINS_ALLERGEN]->(a)",
        "MATCH (i:Ingredient) WHERE i.name_cn CONTAINS '坚果' OR i.name_cn CONTAINS '核桃' OR i.name_cn CONTAINS '腰果' OR i.name_en CONTAINS 'nut' MERGE (a:Allergen {name_cn: '坚果', name_en: 'Tree Nuts'}) MERGE (i)-[:CONTAINS_ALLERGEN]->(a)",
        "MATCH (i:Ingredient) WHERE i.name_cn CONTAINS '大豆' OR i.name_cn CONTAINS '黄豆' OR i.name_cn CONTAINS '豆腐' OR i.name_en CONTAINS 'soy' MERGE (a:Allergen {name_cn: '大豆', name_en: 'Soybeans'}) MERGE (i)-[:CONTAINS_ALLERGEN]->(a)",
        "MATCH (i:Ingredient) WHERE i.name_cn CONTAINS '牛奶' OR i.name_cn CONTAINS '奶酪' OR i.name_cn CONTAINS '黄油' OR i.name_en CONTAINS 'milk' OR i.name_en CONTAINS 'dairy' MERGE (a:Allergen {name_cn: '牛奶', name_en: 'Milk/Dairy'}) MERGE (i)-[:CONTAINS_ALLERGEN]->(a)",
        "MATCH (i:Ingredient) WHERE i.name_cn CONTAINS '鸡蛋' OR i.name_cn CONTAINS '蛋黄' OR i.name_en CONTAINS 'egg' MERGE (a:Allergen {name_cn: '鸡蛋', name_en: 'Eggs'}) MERGE (i)-[:CONTAINS_ALLERGEN]->(a)",
        "MATCH (i:Ingredient) WHERE i.name_cn CONTAINS '鱼' OR i.name_en CONTAINS 'fish' MERGE (a:Allergen {name_cn: '鱼类', name_en: 'Fish'}) MERGE (i)-[:CONTAINS_ALLERGEN]->(a)",
        "MATCH (i:Ingredient) WHERE i.name_cn CONTAINS '虾' OR i.name_cn CONTAINS '蟹' OR i.name_cn CONTAINS '海鲜' OR i.name_en CONTAINS 'shrimp' OR i.name_en CONTAINS 'crab' OR i.name_en CONTAINS 'seafood' MERGE (a:Allergen {name_cn: '甲壳类海鲜', name_en: 'Crustaceans'}) MERGE (i)-[:CONTAINS_ALLERGEN]->(a)",
        "MATCH (i:Ingredient) WHERE i.name_cn CONTAINS '小麦' OR i.name_cn CONTAINS '面粉' OR i.name_en CONTAINS 'wheat' OR i.name_en CONTAINS 'flour' MERGE (a:Allergen {name_cn: '麸质/小麦', name_en: 'Wheat/Gluten'}) MERGE (i)-[:CONTAINS_ALLERGEN]->(a)",
        "MATCH (i:Ingredient) WHERE i.has_allium = true MERGE (a:Allergen {name_cn: '五辛', name_en: 'Allium'}) MERGE (i)-[:CONTAINS_ALLERGEN]->(a)"
    ]

    # 查询：导入外挂计算节点 - 烹饪方式
    import_cooking_query = """
    MERGE (c:CookingMethod {id: $method_id})
    SET c.name = $name,
        c.kcal_multi = $kcal_multi,
        c.fat_multi = $fat_multi,
        c.water_loss_rate = $water_loss_rate
    """

    # 查询：导入外挂计算节点 - 调味基底
    import_seasoning_query = """
    MERGE (s:SeasoningProfile {id: $profile_id})
    SET s.name = $name,
        s.na_density_mg = $na_density_mg,
        s.sugar_density_g = $sugar_density_g,
        s.k_density_kcal = $k_density_kcal
    """

    # 查询：导入复合菜谱并挂载三维关系 (食材、烹饪、调味)
    import_recipe_query = """
    MERGE (r:Recipe {id: $recipe_id})
    SET r.name_cn = $recipe_name,
        r.name_en = $english_name,
        r.category = $category,
        r.is_breakfast = $is_breakfast,
        r.is_soup = $is_soup
    
    WITH r
    MATCH (i:Ingredient {id: $ingredient_id})
    MERGE (r)-[:CONTAINS_INGREDIENT {weight_ratio: $weight_ratio}]->(i)
    
    WITH r
    MATCH (cm:CookingMethod {id: $method_id})
    MERGE (r)-[:COOKED_BY]->(cm)
    
    WITH r
    MATCH (sp:SeasoningProfile {id: $profile_id})
    MERGE (r)-[:SEASONED_BY]->(sp)
    """

    # ---------------- 2. 执行数据流注入 ----------------

    print("🧹 1. 正在彻底清空旧图谱数据库...")
    with GraphDatabase.driver(URI, auth=AUTH) as driver:
        with driver.session() as session:
            session.run(clear_query)
            print("✅ 数据库已清空！")

            # --- 步骤 1：导入基础食材 ---
            print("🚀 2. 开始注入基础食材与营养结构...")
            with open(ingredients_file, mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                count_ing = 0
                for row in reader:
                    params = {
                        "item_id": row["item_id"].strip(),
                        "category": row.get("category", "Unknown").strip(),
                        "sub_category": row.get("sub_category", "Unknown").strip(),
                        "name_cn": row.get("name_cn", "").strip(),
                        "name_en": row.get("name_en", "").strip(),
                        "is_halal": row.get("is_halal", "true").strip().lower() == "true",
                        "is_vegan": row.get("is_vegan", "false").strip().lower() == "true",
                        "has_allium": row.get("has_allium", "false").strip().lower() == "true",
                        "gi_level": int(row.get("gi_level", "3").strip() or 3),
                        "constraint_type": row.get("constraint_type", "").strip(),
                        "price_tier": int(row.get("price_tier", "1").strip() or 1),
                        "energy_kcal": safe_float(row.get("energy_kcal")),
                        "protein_g": safe_float(row.get("protein_g")),
                        "fat_g": safe_float(row.get("fat_g")),
                        "carb_g": safe_float(row.get("carb_g")),
                        # 兼容新版微量元素字段 (若原CSV没有这几列，将默认设为 0.0)
                        "fiber_g": safe_float(row.get("fiber_g")),
                        "sodium_mg": safe_float(row.get("sodium_mg")),
                        "sugar_g": safe_float(row.get("sugar_g")),
                        "potassium_mg": safe_float(row.get("potassium_mg")),
                        "phosphorus_mg": safe_float(row.get("phosphorus_mg")),
                        "purine_mg": safe_float(row.get("purine_mg"))
                    }
                    session.run(import_ingredient_query, **params)
                    count_ing += 1
            print(f"✅ 成功导入 {count_ing} 种食材架构！")

            # --- 步骤 2：生成过敏原 ---
            print("🧠 3. 开始执行 AI 过敏原与禁忌推理引擎...")
            for q in allergen_queries:
                session.run(q)
            print("✅ 过敏原禁忌网络生成完毕！")

            # --- 步骤 3：导入外挂维度节点 (容错处理：如果文件不存在则跳过并提示) ---
            print("🔥 4. 导入烹饪矩阵...")
            try:
                with open(cooking_file, mode='r', encoding='utf-8') as f:
                    for row in csv.DictReader(f):
                        session.run(import_cooking_query, 
                            method_id=row["method_id"].strip(),
                            name=row["name"].strip(),
                            kcal_multi=safe_float(row["kcal_multi"], 1.0),
                            fat_multi=safe_float(row["fat_multi"], 1.0),
                            water_loss_rate=safe_float(row["water_loss_rate"], 1.0)
                        )
                print("✅ 烹饪矩阵注入完毕！")
            except FileNotFoundError:
                print("⚠️ 未检测到 cooking_methods.csv，引擎将采用内置默认烹饪系数。")
                # 创建一个默认节点防呆
                session.run(import_cooking_query, method_id="CM_001", name="标准做法", kcal_multi=1.0, fat_multi=1.0, water_loss_rate=1.0)

            print("🧂 5. 导入调味基底...")
            try:
                with open(seasoning_file, mode='r', encoding='utf-8') as f:
                    for row in csv.DictReader(f):
                        session.run(import_seasoning_query, 
                            profile_id=row["profile_id"].strip(),
                            name=row["name"].strip(),
                            na_density_mg=safe_float(row["na_density_mg"], 5.0),
                            sugar_density_g=safe_float(row["sugar_density_g"], 0.0),
                            k_density_kcal=safe_float(row["k_density_kcal"], 0.5)
                        )
                print("✅ 调味基底注入完毕！")
            except FileNotFoundError:
                print("⚠️ 未检测到 seasoning_profiles.csv，引擎将采用内置清淡调味基底。")
                # 创建一个默认节点防呆
                session.run(import_seasoning_query, profile_id="SP_001", name="基础调味", na_density_mg=5.0, sugar_density_g=0.0, k_density_kcal=0.5)

            # --- 步骤 4：整合最终菜谱关系网 ---
            print("🍳 6. 开始构建复合菜谱物理网络(Recipe Graph)...")
            with open(recipes_file, mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                count_rec = 0
                for row in reader:
                    params = {
                        "recipe_id": row.get("recipe_id", "").strip(),
                        "recipe_name": row.get("recipe_name_cn", "").strip(),
                        "english_name": row.get("recipe_name_en", "").strip(),
                        "category": row.get("type", "").strip(),       
                        "ingredient_id": row.get("ingredient_id", "").strip(),
                        "weight_ratio": safe_float(row.get("min_pct")),
                        "is_breakfast": row.get("is_breakfast", "false").strip().upper() == "TRUE",
                        "is_soup": row.get("is_soup", "false").strip().upper() == "TRUE",
                        # 新增两个关联字段，若CSV中未提供则给默认兜底 ID
                        "method_id": row.get("method_id", "CM_001").strip() or "CM_001",
                        "profile_id": row.get("profile_id", "SP_001").strip() or "SP_001"
                    }
                    session.run(import_recipe_query, **params)
                    count_rec += 1
            print(f"✅ 成功织入 {count_rec} 条菜谱-食材构成关联！")
            print("🚀 图谱重构与升级圆满完成！")

if __name__ == "__main__":
    # 确保根目录下备齐了这四份文件
    reset_and_import(
        ingredients_file="advanced_ingredients.csv", 
        recipes_file="recipes.csv",
        cooking_file="cooking_methods.csv",
        seasoning_file="seasoning_profiles.csv"
    )