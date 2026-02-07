#!/bin/bash

# Non-interactive Claude runner script
# This script ensures Claude runs without prompting for yes/no confirmation

set -e  # Continue on error but handle it

# Get configuration from environment variables
CLAUDE_ENTRY=${CLAUDE_ENTRY:-"ccr"}
CLAUDE_MODE=${CLAUDE_MODE:-"code"}
CLAUDE_SKILL_INBOX=${CLAUDE_SKILL_INBOX:-"/inbox-orchestrator"}  # Keep leading slash as per config
TIMEOUT_SECONDS=${CLAUDE_TIMEOUT_SECONDS:-"180"}
VAULT_PATH=${VAULT_PATH:-"/mnt/c/AI_Hackthon"}
INBOX_DIR=${INBOX_DIR:-"INBOX"}
NEEDS_ACTION_DIR=${NEEDS_ACTION_DIR:-"NEEDS_ACTION"}

# Set timeout command
TIMEOUT_CMD="timeout ${TIMEOUT_SECONDS}s"

# Create timestamp for log identification
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

echo "[${TIMESTAMP}] Starting Claude runner with entry: $CLAUDE_ENTRY, mode: $CLAUDE_MODE, skill: $CLAUDE_SKILL_INBOX"

# Change to the project directory
cd /home/syedhuzaifa/final_hackthon_0

# Continuous processing loop - keep running until all queues are empty
PROCESSED_ANYTHING=true

while [ "$PROCESSED_ANYTHING" = true ]; do
    PROCESSED_ANYTHING=false

    # Execute the inbox-orchestrator skill to process files (INBOX and NEEDS_ACTION)
    if [ -f "/home/syedhuzaifa/final_hackthon_0/.claude/skills/inbox-orchestrator/scripts/triage_inbox.py" ]; then
        # Check if there are files to process
        INBOX_COUNT=$(ls -A "$VAULT_PATH/$INBOX_DIR/" 2>/dev/null | wc -l)
        NEEDS_ACTION_COUNT=$(ls -A "$VAULT_PATH/$NEEDS_ACTION_DIR/" 2>/dev/null | wc -l)

        TOTAL_PENDING=$((INBOX_COUNT + NEEDS_ACTION_COUNT))

        if [ $TOTAL_PENDING -gt 0 ]; then
            echo "[${TIMESTAMP}] Processing $TOTAL_PENDING total items (INBOX: $INBOX_COUNT, NEEDS_ACTION: $NEEDS_ACTION_COUNT)"
            $TIMEOUT_CMD python /home/syedhuzaifa/final_hackthon_0/.claude/skills/inbox-orchestrator/scripts/triage_inbox.py "$VAULT_PATH"

            # After processing, check if anything was actually processed
            # by comparing file counts before and after
            INBOX_AFTER=$(ls -A "$VAULT_PATH/$INBOX_DIR/" 2>/dev/null | wc -l)
            NEEDS_ACTION_AFTER=$(ls -A "$VAULT_PATH/$NEEDS_ACTION_DIR/" 2>/dev/null | wc -l)

            TOTAL_AFTER=$((INBOX_AFTER + NEEDS_ACTION_AFTER))

            if [ $TOTAL_AFTER -lt $TOTAL_PENDING ]; then
                PROCESSED_ANYTHING=true
                echo "[${TIMESTAMP}] Processed some tasks, continuing loop..."
            else
                # No more tasks were processed, break the loop
                break
            fi
        else
            echo "[${TIMESTAMP}] No tasks in INBOX or NEEDS_ACTION, exiting loop"
            break
        fi
    else
        # Fallback: Run Claude with the skill if direct script not available
        echo "[${TIMESTAMP}] Using fallback method with Claude skill"
        if timeout $TIMEOUT_SECONDS bash -c "echo 'y' | $CLAUDE_ENTRY $CLAUDE_MODE --print '$CLAUDE_SKILL_INBOX $VAULT_PATH'"; then
            echo "[${TIMESTAMP}] Claude skill executed successfully"
        else
            echo "[${TIMESTAMP}] Claude skill execution failed"
            exit 1
        fi
        break
    fi

    # Small delay to prevent rapid looping
    sleep 2
done

echo "[${TIMESTAMP}] Claude runner completed successfully - all tasks processed"
exit 0
