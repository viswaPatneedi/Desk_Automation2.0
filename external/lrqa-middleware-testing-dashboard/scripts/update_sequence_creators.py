#!/usr/bin/env python3
"""
Update all existing sequences to have created_by set to vpatne290
This fixes legacy sequences that have NULL created_by values.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import Session, SavedSequence
from sqlalchemy import text
from datetime import datetime


def get_user_id_by_username(username):
    """Verify username exists and get it"""
    # Since users are stored in JSON, just return the username
    # The created_by field will store the username string directly
    print(f"✅ Setting creator to: {username}")
    return username


def update_sequences_creator(creator_username, dry_run=False):
    """Update all sequences with NULL created_by to the specified username"""
    session = Session()
    try:
        # Find all sequences with NULL created_by
        null_sequences = session.query(SavedSequence).filter(
            SavedSequence.created_by.is_(None)
        ).all()
        
        if not null_sequences:
            print("✅ All sequences already have creators assigned!")
            return 0
        
        print(f"\n📊 Found {len(null_sequences)} sequences with NULL created_by\n")
        print("Sequences to update:")
        for seq in null_sequences[:10]:  # Show first 10
            print(f"  • {seq.name} (ID: {seq.seq_id})")
        if len(null_sequences) > 10:
            print(f"  ... and {len(null_sequences) - 10} more")
        
        if dry_run:
            print(f"\n📋 DRY RUN: Would update {len(null_sequences)} sequences")
            return len(null_sequences)
        
        # Update all sequences using raw SQL - store username as text
        session.execute(
            text(f"UPDATE saved_sequences SET created_by = '{creator_username}', updated_at = NOW() WHERE created_by IS NULL")
        )
        session.commit()
        
        print(f"\n✅ Successfully updated {len(null_sequences)} sequences!")
        print(f"   All sequences now have created_by = '{creator_username}'\n")
        return len(null_sequences)
        
    except Exception as e:
        session.rollback()
        print(f"❌ Error updating sequences: {e}")
        return -1
    finally:
        session.close()


def verify_update():
    """Verify that all sequences have created_by set"""
    session = Session()
    try:
        # Use raw SQL to count
        null_result = session.execute(text("SELECT COUNT(*) FROM saved_sequences WHERE created_by IS NULL")).fetchone()
        total_result = session.execute(text("SELECT COUNT(*) FROM saved_sequences")).fetchone()
        
        null_count = null_result[0] if null_result else 0
        total_count = total_result[0] if total_result else 0
        
        print(f"\n📈 Verification:")
        print(f"   Total sequences: {total_count}")
        print(f"   Sequences with NULL created_by: {null_count}")
        print(f"   Sequences with creator: {total_count - null_count}")
        
        if null_count == 0:
            print(f"\n✅ All sequences have creators assigned!\n")
            return True
        else:
            print(f"\n⚠️  Still {null_count} sequences without creators\n")
            return False
    finally:
        session.close()


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Update sequence creators from NULL to vpatne290'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without modifying database'
    )
    parser.add_argument(
        '--username',
        default='vpatne290',
        help='Username to set as creator (default: vpatne290)'
    )
    
    args = parser.parse_args()
    
    print("\n" + "="*70)
    print("  Sequence Creator Update Utility")
    print("="*70)
    print(f"  Target Username: {args.username}")
    print(f"  Mode: {'DRY RUN (preview only)' if args.dry_run else 'LIVE UPDATE'}")
    print("="*70 + "\n")
    
    # Get user  
    creator_username = get_user_id_by_username(args.username)
    if not creator_username:
        print("❌ Cannot proceed\n")
        return 1
    
    # Update sequences
    updated = update_sequences_creator(creator_username, dry_run=args.dry_run)
    if updated < 0:
        print("❌ Update failed\n")
        return 1
    
    # Verify
    if not args.dry_run:
        verify_update()
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
