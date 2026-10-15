"""Naming for the realistic hair object (one per character body)."""


def hair_name_for(target_obj):
    return f"Wisp_Hair_{target_obj.name}"


def find_hair(bpy_data, target_obj):
    if target_obj is None:
        return None
    return bpy_data.objects.get(hair_name_for(target_obj))
