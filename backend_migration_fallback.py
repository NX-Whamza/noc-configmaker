
def apply_intelligent_translation(source_config, source_device_info, source_syntax_info, target_syntax_info, target_device_info, target_version):
    """
    Apply intelligent rule-based translation (Fallback logic)
    Used when AI is disabled or fails validation.
    """
    safe_print(f"[INTELLIGENT TRANSLATION] Starting rule-based migration from {source_device_info['model']} to {target_device_info['model']}...")

    # 1. Build comprehensive interface map
    # We use the source/target models from the info dicts
    # If exact model match fails, we try to detect best fit
    source_model = source_device_info.get('type') or source_device_info.get('model')
    target_model = target_device_info.get('type') or target_device_info.get('model')
    
    # Ensure keys exist in ROUTERBOARD_INTERFACES
    # If not, try to map 'rb5009' -> 'RB5009UG+S+' etc.
    # (The keys in ROUTERBOARD_INTERFACES are now full names like 'RB5009UG+S+')
    # But validation logic earlier uses detection which returns full names.
    
    safe_print(f"[MAPPING] Building interface map for {source_model} -> {target_model}")
    interface_map = build_interface_migration_map(source_model, target_model)
    
    if not interface_map:
        safe_print(f"[WARNING] Could not build interface map. Using identity mapping.")
        interface_map = {'ether1': 'ether1'}  # Fallback

    # 2. Apply interface migration (renaming ports in config)
    migrated_config = migrate_interface_config(source_config, interface_map)

    # 3. Apply Syntax Conversion (ROS6 -> ROS7) if needed
    if str(target_version).startswith('7'):
        safe_print("[SYNTAX] Applying ROS6 -> ROS7 syntax usage...")
        migrated_config = apply_ros6_to_ros7_syntax(migrated_config)

    # 4. Standardize BGP/OSPF if not fully covered by simple replacement
    # (apply_ros6_to_ros7_syntax covers basic paths, but we might need more)
    # Ensure 'routing bgp connection' is used
    if '/routing bgp peer' in migrated_config and str(target_version).startswith('7'):
         migrated_config = migrated_config.replace('/routing bgp peer', '/routing bgp connection')

    return migrated_config
