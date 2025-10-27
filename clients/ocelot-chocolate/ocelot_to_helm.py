#!/usr/bin/env python3
"""
Ocelot to Helm Inventory Mapper
Maps Ocelot product data from Faire export to Helm inventory format
"""

import csv
import sys
from pathlib import Path
from typing import Dict, List


def clean_field(value):
    """Clean and normalize field values"""
    if value is None or value == '':
        return ''
    return str(value).strip()


def map_ocelot_to_helm(ocelot_row: Dict) -> Dict:
    """
    Map a single Ocelot product row to Helm inventory format
    
    Args:
        ocelot_row: Dictionary containing Ocelot product data
        
    Returns:
        Dictionary with Helm inventory fields
    """
    # Extract key fields from Ocelot data
    sku = clean_field(ocelot_row.get('SKU', ''))
    product_name = clean_field(ocelot_row.get('Product Name (English)', ''))
    description = clean_field(ocelot_row.get('Description (English)', ''))
    
    # Weight conversion (Ocelot uses g, kg, lb, oz - Helm needs kg)
    item_weight = clean_field(ocelot_row.get('Item Weight', ''))
    item_weight_unit = clean_field(ocelot_row.get('Item Weight Unit', ''))
    weight_kg = convert_to_kg(item_weight, item_weight_unit)
    
    # Dimensions (convert to cm if needed)
    height = convert_to_cm(
        clean_field(ocelot_row.get('Item Height', '')),
        clean_field(ocelot_row.get('Item Dimensions Unit', ''))
    )
    width = convert_to_cm(
        clean_field(ocelot_row.get('Item Width', '')),
        clean_field(ocelot_row.get('Item Dimensions Unit', ''))
    )
    length = convert_to_cm(
        clean_field(ocelot_row.get('Item Length', '')),
        clean_field(ocelot_row.get('Item Dimensions Unit', ''))
    )
    
    # Barcode (GTIN)
    barcode = clean_field(ocelot_row.get('GTIN', ''))
    
    # Price (use GBR wholesale price)
    wholesale_price = clean_field(ocelot_row.get('GBR Unit Wholesale Price', ''))
    retail_price = clean_field(ocelot_row.get('GBR Unit Retail Price', ''))
    
    # HS Code and Country
    hs_code = clean_field(ocelot_row.get('HS6 Tariff Code', ''))
    country_of_origin = clean_field(ocelot_row.get('Made In Country', ''))
    
    # Inventory level
    on_hand_inventory = clean_field(ocelot_row.get('On Hand Inventory', ''))
    
    # Build option name from Option 1, 2, 3 values if they exist
    option_parts = []
    for i in range(1, 4):
        opt_name = clean_field(ocelot_row.get(f'Option {i} Name', ''))
        opt_value = clean_field(ocelot_row.get(f'Option {i} Value', ''))
        if opt_name and opt_value:
            option_parts.append(f"{opt_value}")
    
    # Create full name with options
    full_name = product_name
    if option_parts:
        full_name = f"{product_name} - {' '.join(option_parts)}"
    
    # Map to Helm format
    helm_row = {
        'Inventory ID': '',  # Leave empty for new entries
        'SKU': sku,
        'Secondary SKU': '',
        'Name': full_name,
        'Type (1: Inventory, 2: Component, 3: Group)': '1',  # Inventory type
        'Batching Type (0: No Batching, 2: Batch Numbers)': '0',
        'Serial Numbered (0: No, 1: Yes)': '0',
        'Sync Stock': '',
        'Dont Sync Until': '',
        'Product Weight (Kg)': weight_kg,
        'Product Height (cm)': height,
        'Product Width (cm)': width,
        'Product Length (cm)': length,
        'Item Barcode': barcode,
        'Item Barcode 2': '',
        'Item Barcode 3': '',
        'Item Barcode 4': '',
        'Item Barcode 5': '',
        'Picking by Packaging (0: No, 1: Yes)': '0',
        'Default Packaging Inventory (SKU)': '',
        'Description': description[:500] if description else '',  # Limit description length
        'Cost Price': wholesale_price,
        'Unit Price': retail_price,
        'HS Code': hs_code,
        'Country of Origin': country_of_origin,
        'Customs Description': product_name[:100] if product_name else '',
        'Include Assembly Stock Level (1: Yes, 0: No)': '0',
        'Include PO Stock Level (1: Yes, 0: No)': '1',
        'Dropshipping Type (1: Enabled, 0: Disabled)': '0',
        'Dynamic Components Type (1: Enabled, 0: Disabled)': '0',
        'Global Stock Warning Level': '5',  # Default warning level
        'Fabric Content': '',
        'Image URL': clean_field(ocelot_row.get('Option Image', '')),
        'Service Option': '',
        'Is Archived': '0' if clean_field(ocelot_row.get('Product Status', 'Published')) == 'Published' else '1',
        'Tags': '',
        'Fulfilment Client': ''
    }
    
    return helm_row


def convert_to_kg(weight: str, unit: str) -> str:
    """Convert weight to kilograms"""
    if not weight or not unit:
        return ''
    
    try:
        weight_float = float(weight)
        unit = unit.lower()
        
        if unit == 'kg':
            return str(weight_float)
        elif unit == 'g':
            return str(weight_float / 1000)
        elif unit == 'lb':
            return str(weight_float * 0.453592)
        elif unit == 'oz':
            return str(weight_float * 0.0283495)
        else:
            return weight
    except (ValueError, TypeError):
        return ''


def convert_to_cm(dimension: str, unit: str) -> str:
    """Convert dimension to centimeters"""
    if not dimension or not unit:
        return ''
    
    try:
        dim_float = float(dimension)
        unit = unit.lower()
        
        if unit == 'cm':
            return str(dim_float)
        elif unit == 'in':
            return str(dim_float * 2.54)
        else:
            return dimension
    except (ValueError, TypeError):
        return ''


def process_ocelot_file(input_file: str, output_file: str):
    """
    Process Ocelot CSV and generate Helm inventory CSV
    
    Args:
        input_file: Path to Ocelot products CSV
        output_file: Path for output Helm inventory CSV
    """
    print(f"Reading Ocelot data from: {input_file}")
    
    # Read Ocelot data
    ocelot_products = []
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Skip header rows that don't contain product data
            if row.get('Product Name (English)') in ['Product Name (English)', 'Mandatory']:
                continue
            # Skip unpublished or deleted products
            status = clean_field(row.get('Product Status', 'Published'))
            if status in ['Unpublished', 'Deleted', 'Draft']:
                print(f"Skipping {status} product: {row.get('Product Name (English)')}")
                continue
            ocelot_products.append(row)
    
    print(f"Found {len(ocelot_products)} products to process")
    
    # Map to Helm format
    helm_inventory = []
    for ocelot_row in ocelot_products:
        try:
            helm_row = map_ocelot_to_helm(ocelot_row)
            helm_inventory.append(helm_row)
        except Exception as e:
            print(f"Error processing row: {e}")
            print(f"Product: {ocelot_row.get('Product Name (English)')}")
            continue
    
    print(f"Mapped {len(helm_inventory)} products to Helm format")
    
    # Write output
    if helm_inventory:
        helm_fieldnames = [
            'Inventory ID', 'SKU', 'Secondary SKU', 'Name',
            'Type (1: Inventory, 2: Component, 3: Group)',
            'Batching Type (0: No Batching, 2: Batch Numbers)',
            'Serial Numbered (0: No, 1: Yes)', 'Sync Stock', 'Dont Sync Until',
            'Product Weight (Kg)', 'Product Height (cm)', 'Product Width (cm)',
            'Product Length (cm)', 'Item Barcode', 'Item Barcode 2',
            'Item Barcode 3', 'Item Barcode 4', 'Item Barcode 5',
            'Picking by Packaging (0: No, 1: Yes)',
            'Default Packaging Inventory (SKU)', 'Description',
            'Cost Price', 'Unit Price', 'HS Code', 'Country of Origin',
            'Customs Description', 'Include Assembly Stock Level (1: Yes, 0: No)',
            'Include PO Stock Level (1: Yes, 0: No)',
            'Dropshipping Type (1: Enabled, 0: Disabled)',
            'Dynamic Components Type (1: Enabled, 0: Disabled)',
            'Global Stock Warning Level', 'Fabric Content', 'Image URL',
            'Service Option', 'Is Archived', 'Tags', 'Fulfilment Client'
        ]
        
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=helm_fieldnames)
            writer.writeheader()
            writer.writerows(helm_inventory)
        
        print(f"Successfully wrote Helm inventory to: {output_file}")
    else:
        print("No products to write!")


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python ocelot_to_helm_inventory.py <ocelot_products.csv> [output.csv]")
        print("\nExample:")
        print("  python ocelot_to_helm_inventory.py OcelotProducts.csv helm_inventory.csv")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else 'helm_inventory_export.csv'
    
    if not Path(input_file).exists():
        print(f"Error: Input file not found: {input_file}")
        sys.exit(1)
    
    try:
        process_ocelot_file(input_file, output_file)
        print("\n✓ Conversion completed successfully!")
    except Exception as e:
        print(f"\n✗ Error during conversion: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()