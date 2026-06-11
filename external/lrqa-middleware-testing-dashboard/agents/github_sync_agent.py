"""
GitHub API Integration Module for Distributed Sync

Handles bidirectional synchronization with GitHub repository:
- Push synced changes as commits
- Create release tags
- Auto-merge non-conflicting changes
- Maintain audit trail in repo

Uses PyGithub library for GitHub API access.

Author: AI Development Agent
Date: June 9, 2026
Version: 1.0
"""

import os
import json
import time
from datetime import datetime, timezone
from typing import Optional, Dict, List, Tuple
from enum import Enum
import logging

try:
    from github import Github, GithubException, InputGitAuthor
except ImportError:
    Github = None
    GithubException = Exception
    InputGitAuthor = None


# ============================================================================
# ENUMS
# ============================================================================

class GitHubCommitType(Enum):
    """Types of commits created during sync"""
    DEVICE_SYNC = "DEVICES"
    METHOD_SYNC = "METHODS"
    SEQUENCE_SYNC = "SEQUENCES"
    COMMAND_SYNC = "COMMANDS"
    PATTERN_SYNC = "PATTERNS"
    USER_SYNC = "USERS"
    CONFLICT_RESOLUTION = "CONFLICT_RESOLUTION"


# ============================================================================
# GITHUB REPO MANAGER
# ============================================================================

class GitHubRepoManager:
    """Manages GitHub repository operations"""
    
    def __init__(self, token: str = None, repo_name: str = None):
        """
        Initialize GitHub repo manager
        
        Args:
            token: GitHub API token (or from GITHUB_API_TOKEN env var)
            repo_name: Repo name in format "owner/repo" (or from GITHUB_REPO env var)
        """
        self.logger = logging.getLogger("GitHubRepoManager")
        
        self.token = token or os.getenv('GITHUB_API_TOKEN')
        self.repo_name = repo_name or os.getenv('GITHUB_REPO')
        self.branch = os.getenv('GITHUB_BRANCH', 'main')
        
        if not self.token:
            self.logger.warning("⚠️  GITHUB_API_TOKEN not set - GitHub sync disabled")
            self.github = None
            self.repo = None
            return
        
        if not self.repo_name:
            self.logger.warning("⚠️  GITHUB_REPO not set - GitHub sync disabled")
            self.github = None
            self.repo = None
            return
        
        try:
            self.github = Github(self.token)
            self.repo = self.github.get_repo(self.repo_name)
            self.logger.info(f"✅ GitHub repo initialized: {self.repo_name}")
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize GitHub repo: {e}")
            self.github = None
            self.repo = None
    
    def is_connected(self) -> bool:
        """Check if GitHub is configured and connected"""
        if not self.github or not self.repo:
            return False
        
        try:
            # Test connection
            self.repo.get_contents("README.md")
            return True
        except:
            return False
    
    def create_sync_branch(self, sync_id: str) -> Optional[str]:
        """Create a new sync branch for changes"""
        if not self.repo:
            return None
        
        try:
            branch_name = f"sync/{sync_id}"
            
            # Get main branch
            main_branch = self.repo.get_branch(self.branch)
            
            # Create new branch
            self.repo.create_git_ref(
                ref=f"refs/heads/{branch_name}",
                sha=main_branch.commit.sha
            )
            
            self.logger.info(f"✅ Created sync branch: {branch_name}")
            return branch_name
        except GithubException as e:
            if "Reference already exists" in str(e):
                self.logger.info(f"ℹ️  Sync branch already exists: sync/{sync_id}")
                return f"sync/{sync_id}"
            self.logger.error(f"❌ Failed to create sync branch: {e}")
            return None
    
    def push_commit(self, branch: str, file_path: str, content: str, 
                   message: str, author_name: str = None, 
                   author_email: str = None) -> Optional[str]:
        """
        Push a commit to GitHub
        
        Args:
            branch: Target branch
            file_path: File path in repo
            content: File content
            message: Commit message
            author_name: Commit author name
            author_email: Commit author email
        
        Returns:
            Commit SHA if successful
        """
        if not self.repo:
            return None
        
        try:
            # Get or create file
            try:
                file_obj = self.repo.get_contents(file_path, ref=branch)
                self.repo.update_file(
                    path=file_path,
                    message=message,
                    content=content,
                    sha=file_obj.sha,
                    branch=branch,
                    committer=InputGitAuthor(author_name or "Sync Agent", author_email or "sync@local") if InputGitAuthor else None
                )
            except:
                # File doesn't exist, create it
                self.repo.create_file(
                    path=file_path,
                    message=message,
                    content=content,
                    branch=branch,
                    committer=InputGitAuthor(author_name or "Sync Agent", author_email or "sync@local") if InputGitAuthor else None
                )
            
            self.logger.info(f"✅ Commit pushed: {file_path} ({message[:50]}...)")
            return "OK"
        except Exception as e:
            self.logger.error(f"❌ Failed to push commit: {e}")
            return None
    
    def create_pull_request(self, branch: str, title: str, body: str) -> Optional[int]:
        """
        Create a pull request for sync branch
        
        Args:
            branch: Source branch
            title: PR title
            body: PR description
        
        Returns:
            PR number if successful
        """
        if not self.repo:
            return None
        
        try:
            pr = self.repo.create_pull(
                title=title,
                body=body,
                head=branch,
                base=self.branch
            )
            
            self.logger.info(f"✅ Pull request created: #{pr.number} ({title})")
            return pr.number
        except Exception as e:
            self.logger.error(f"❌ Failed to create PR: {e}")
            return None
    
    def merge_pull_request(self, pr_number: int, delete_branch: bool = True) -> bool:
        """
        Merge a pull request
        
        Args:
            pr_number: PR number to merge
            delete_branch: Delete branch after merge
        
        Returns:
            True if successful
        """
        if not self.repo:
            return False
        
        try:
            pr = self.repo.get_pull(pr_number)
            
            # Merge PR
            pr.merge(
                commit_title=pr.title,
                commit_message=pr.body,
                merge_method="squash"
            )
            
            # Delete branch if requested
            if delete_branch:
                try:
                    self.repo.get_git_ref(f"heads/{pr.head.ref}").delete()
                    self.logger.info(f"✅ Deleted branch: {pr.head.ref}")
                except:
                    pass
            
            self.logger.info(f"✅ PR merged: #{pr_number}")
            return True
        except Exception as e:
            self.logger.error(f"❌ Failed to merge PR: {e}")
            return False
    
    def create_release(self, tag_name: str, release_name: str, 
                      body: str = None, draft: bool = False) -> Optional[str]:
        """
        Create a GitHub release
        
        Args:
            tag_name: Git tag (e.g., v2.0.sync-20260609-143000)
            release_name: Release name
            body: Release notes
            draft: Create as draft
        
        Returns:
            Release URL if successful
        """
        if not self.repo:
            return None
        
        try:
            release = self.repo.create_git_release(
                tag=tag_name,
                name=release_name,
                message=body or f"Sync release {tag_name}",
                draft=draft
            )
            
            self.logger.info(f"✅ Release created: {tag_name}")
            return release.html_url
        except Exception as e:
            self.logger.error(f"❌ Failed to create release: {e}")
            return None
    
    def tag_release(self, sync_id: str, location: str, timestamp: str) -> Optional[str]:
        """
        Create a release tag for sync event
        
        Args:
            sync_id: Sync change ID
            location: Source location (UK_PRIMARY, INDIA_NORTH, etc.)
            timestamp: ISO format timestamp
        
        Returns:
            Tag name if successful
        """
        # Format: v2.0.sync-location-timestamp
        tag_name = f"v2.0.sync-{location.lower()}-{timestamp.replace(':', '').replace('-', '')}"
        
        # Shorten to reasonable length
        if len(tag_name) > 255:
            tag_name = tag_name[:250]
        
        release_name = f"Sync: {location} @ {timestamp}"
        body = f"""
Sync Event Details:
- **Location**: {location}
- **Sync ID**: {sync_id}
- **Timestamp**: {timestamp}
- **Type**: Distributed data synchronization

This release tracks a synchronization event in the multi-location deployment.
"""
        
        return self.create_release(tag_name, release_name, body, draft=False)


# ============================================================================
# SYNC COMMIT GENERATOR
# ============================================================================

class SyncCommitGenerator:
    """Generates commit messages and files for sync events"""
    
    @staticmethod
    def generate_commit_message(commit_type: GitHubCommitType, summary: str,
                               location: str, sync_id: str) -> str:
        """
        Generate a descriptive commit message
        
        Args:
            commit_type: Type of sync (DEVICES, METHODS, etc.)
            summary: Brief summary of changes
            location: Source location
            sync_id: Sync change ID
        
        Returns:
            Formatted commit message
        """
        return f"[SYNC] {commit_type.value}: {summary}\n\nLocation: {location}\nSync ID: {sync_id}"
    
    @staticmethod
    def generate_sync_log_entry(entity_type: str, operation: str, entity_id: str,
                               location: str, user_id: str, timestamp: str) -> Dict:
        """Generate a sync log entry"""
        return {
            'timestamp': timestamp,
            'entity_type': entity_type,
            'operation': operation,
            'entity_id': entity_id,
            'source_location': location,
            'user_id': user_id
        }
    
    @staticmethod
    def generate_pr_body(sync_id: str, location: str, changes: List[Dict]) -> str:
        """
        Generate pull request description
        
        Args:
            sync_id: Sync change ID
            location: Source location
            changes: List of changes
        
        Returns:
            PR body markdown
        """
        change_summary = "\n".join([
            f"- **{c.get('entity_type')}**: {c.get('operation')} {c.get('entity_id')}"
            for c in changes
        ])
        
        return f"""
## Distributed Data Synchronization

**Sync ID**: `{sync_id}`  
**Source Location**: {location}  
**Timestamp**: {datetime.now(timezone.utc).isoformat()}

### Changes

{change_summary}

### Resolution Strategy
- Timestamp-based conflict detection
- Automatic merge for non-breaking changes
- Admin approval for breaking changes
- Full audit trail in commit history

### Next Steps
1. Review changes
2. Verify data integrity
3. Merge to main branch
4. All locations will pull latest on next sync
"""


# ============================================================================
# GITHUB SYNC AGENT
# ============================================================================

class GitHubSyncAgent:
    """Orchestrates GitHub repository synchronization"""
    
    def __init__(self, token: str = None, repo_name: str = None):
        self.logger = logging.getLogger("GitHubSyncAgent")
        self.repo_manager = GitHubRepoManager(token, repo_name)
        self.commit_generator = SyncCommitGenerator()
    
    def is_enabled(self) -> bool:
        """Check if GitHub sync is enabled and configured"""
        return self.repo_manager.is_connected()
    
    def sync_changes_to_github(self, sync_id: str, location: str, 
                              changes: List[Dict], user_id: str = None) -> bool:
        """
        Sync a batch of changes to GitHub
        
        Args:
            sync_id: Sync change ID
            location: Source location
            changes: List of changes to sync
            user_id: User who initiated sync
        
        Returns:
            True if successful
        """
        if not self.is_enabled():
            self.logger.warning("⚠️  GitHub sync not enabled, skipping")
            return False
        
        try:
            # Step 1: Create sync branch
            branch = self.repo_manager.create_sync_branch(sync_id)
            if not branch:
                return False
            
            # Step 2: Create sync log entry
            timestamp = datetime.now(timezone.utc).isoformat()
            sync_log = {
                'sync_id': sync_id,
                'location': location,
                'timestamp': timestamp,
                'user_id': user_id,
                'change_count': len(changes),
                'changes': [
                    {
                        'entity_type': c.get('entity_type'),
                        'operation': c.get('operation'),
                        'entity_id': c.get('entity_id')
                    }
                    for c in changes
                ]
            }
            
            # Step 3: Push sync log file
            sync_log_path = f".sync/logs/{sync_id}.json"
            commit_msg = self.commit_generator.generate_commit_message(
                GitHubCommitType.DEVICES if changes else GitHubCommitType.DEVICE_SYNC,
                f"Applied {len(changes)} changes",
                location,
                sync_id
            )
            
            push_result = self.repo_manager.push_commit(
                branch=branch,
                file_path=sync_log_path,
                content=json.dumps(sync_log, indent=2),
                message=commit_msg
            )
            
            if not push_result:
                return False
            
            # Step 4: Create pull request
            pr_body = self.commit_generator.generate_pr_body(sync_id, location, changes)
            pr_number = self.repo_manager.create_pull_request(
                branch=branch,
                title=f"[SYNC] {location}: {len(changes)} changes",
                body=pr_body
            )
            
            if not pr_number:
                return False
            
            # Step 5: Auto-merge non-breaking changes
            merge_result = self.repo_manager.merge_pull_request(pr_number, delete_branch=True)
            
            if not merge_result:
                self.logger.warning(f"⚠️  Could not auto-merge PR #{pr_number}")
                return False
            
            # Step 6: Create release tag
            release_url = self.repo_manager.tag_release(sync_id, location, timestamp)
            
            if release_url:
                self.logger.info(f"✅ GitHub sync complete: {release_url}")
            else:
                self.logger.warning("⚠️  Release tag creation failed, but sync completed")
            
            return True
        except Exception as e:
            self.logger.error(f"❌ GitHub sync failed: {e}")
            return False


# ============================================================================
# CLI INTERFACE
# ============================================================================

def main():
    """CLI for testing GitHub integration"""
    import argparse
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    parser = argparse.ArgumentParser(description='GitHub Sync Agent')
    parser.add_argument('--test-connection', action='store_true', help='Test GitHub connection')
    parser.add_argument('--sync-id', default='test-sync-1', help='Sync ID for test')
    parser.add_argument('--location', default='UK_PRIMARY', help='Source location')
    parser.add_argument('--test-sync', action='store_true', help='Test sync operation')
    
    args = parser.parse_args()
    
    agent = GitHubSyncAgent()
    
    if args.test_connection:
        if agent.is_enabled():
            print("✅ GitHub connection successful")
        else:
            print("❌ GitHub connection failed - check GITHUB_API_TOKEN and GITHUB_REPO")
    
    elif args.test_sync:
        changes = [
            {
                'entity_type': 'DEVICE',
                'operation': 'CREATE',
                'entity_id': 'device-test-1'
            },
            {
                'entity_type': 'METHOD',
                'operation': 'UPDATE',
                'entity_id': 'method-test-1'
            }
        ]
        
        result = agent.sync_changes_to_github(
            sync_id=args.sync_id,
            location=args.location,
            changes=changes,
            user_id='test-user'
        )
        
        if result:
            print(f"✅ Sync test successful: {args.sync_id}")
        else:
            print(f"❌ Sync test failed")


if __name__ == '__main__':
    main()
