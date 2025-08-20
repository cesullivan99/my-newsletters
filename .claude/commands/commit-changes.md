# Commit Changes

Stage files, commit changes, and push to remote with user approval.

## Optional Arguments: $ARGUMENTS

If arguments are provided, they will be used as the commit message. Otherwise, a commit message will be generated based on the changes.

## Git Workflow Process

1. **Check Repository Status**
   - Run `git status` to see current repository state
   - Identify untracked files and modifications
   - Check for any files that need to be staged

2. **Add Files to Git**
   - Add all relevant untracked files using `git add`
   - Stage all modifications for commit
   - Exclude any files that shouldn't be committed (temporary files, logs, etc.)

3. **Generate Commit Message**
   - If arguments provided, use them as the commit message
   - If no arguments, analyze the staged changes with `git diff --cached`
   - Create a descriptive commit message following the format:
     - Brief summary of changes (50 chars or less)
     - Empty line
     - More detailed explanation if needed
     - Include the Claude Code signature:
       ```
       🤖 Generated with [Claude Code](https://claude.ai/code)
       
       Co-Authored-By: Claude <noreply@anthropic.com>
       ```

4. **Single User Approval Point**
   - Show the proposed commit message to the user
   - List all files that will be committed
   - Ask for explicit user approval before proceeding with commit AND push
   - Wait for confirmation before executing both commit and push

5. **Execute Commit and Push**
   - Only proceed after user confirms approval
   - Run `git commit` with the approved message
   - Immediately run `git push` to update remote repository
   - Confirm successful commit and push with final status
   - Show commit hash and push summary

## Safety Measures

- Never commit without explicit user approval
- Don't commit sensitive files (check .gitignore patterns)
- Don't commit temporary or build artifacts
- Always show what will be committed before proceeding

## Example Usage

```
/commit-changes "Add new feature for user authentication"
```

or

```
/commit-changes
```

(This will auto-generate a commit message based on the changes)