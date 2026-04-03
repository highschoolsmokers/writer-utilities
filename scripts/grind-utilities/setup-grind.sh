#!/usr/bin/env bash
set -euo pipefail

# setup-grind.sh — Import contacts into a "Grind" group and create a Mail rule
# Usage: ./setup-grind.sh [contacts-file]
#   Default contacts file: grind-contacts.txt in the same directory as this script

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONTACTS_FILE="${1:-$SCRIPT_DIR/grind-contacts.txt}"
GROUP_NAME="Grind"
MAILBOX_NAME="Grind"

if [[ ! -f "$CONTACTS_FILE" ]]; then
  echo "Error: contacts file not found: $CONTACTS_FILE" >&2
  exit 1
fi

# ── Parse contacts file ──────────────────────────────────────────────
declare -a NAMES=()
declare -a EMAILS=()

while IFS= read -r line; do
  # Skip comments and blank lines
  line="$(echo "$line" | sed 's/^[[:space:]]*//' | sed 's/[[:space:]]*$//')"
  [[ -z "$line" || "$line" == \#* ]] && continue

  # Split on comma: "First Last, email@example.com"
  name="$(echo "$line" | cut -d',' -f1 | sed 's/^[[:space:]]*//' | sed 's/[[:space:]]*$//')"
  email="$(echo "$line" | cut -d',' -f2 | sed 's/^[[:space:]]*//' | sed 's/[[:space:]]*$//')"

  if [[ -z "$name" || -z "$email" ]]; then
    echo "Warning: skipping malformed line: $line" >&2
    continue
  fi

  NAMES+=("$name")
  EMAILS+=("$email")
done < "$CONTACTS_FILE"

if [[ ${#EMAILS[@]} -eq 0 ]]; then
  echo "Error: no contacts found in $CONTACTS_FILE" >&2
  exit 1
fi

echo "Found ${#EMAILS[@]} contact(s) to process."

# ── 1. Create "Grind" group in Contacts.app (idempotent) ────────────
echo "Setting up Contacts group '$GROUP_NAME'..."

osascript <<'APPLESCRIPT'
tell application "Contacts"
  if not (exists group "Grind") then
    make new group with properties {name:"Grind"}
    save
  end if
end tell
APPLESCRIPT

# ── 2. Add each contact to the Grind group ──────────────────────────
for i in "${!EMAILS[@]}"; do
  email="${EMAILS[$i]}"
  full_name="${NAMES[$i]}"

  # Split name into first/last
  first="$(echo "$full_name" | awk '{print $1}')"
  last="$(echo "$full_name" | awk '{$1=""; print}' | sed 's/^[[:space:]]*//')"

  echo "  Adding: $full_name <$email>"

  osascript - "$first" "$last" "$email" <<'APPLESCRIPT'
on run argv
  set firstName to item 1 of argv
  set lastName to item 2 of argv
  set emailAddr to item 3 of argv

  tell application "Contacts"
    set grindGroup to group "Grind"

    -- Check if already in the Grind group (nothing to do)
    set inGroup to (every person of grindGroup whose value of emails contains emailAddr)
    if (count of inGroup) > 0 then
      return "already in group"
    end if

    -- Check if contact with this email exists anywhere
    set existingPeople to (every person whose value of emails contains emailAddr)

    if (count of existingPeople) > 0 then
      -- Try to add the existing contact to the group.
      -- This fails for linked/unified/iCloud contacts with error:
      --   "You can only add a person to a group. (1)"
      -- In that case, fall back to creating a new local contact.
      set addedOK to false
      repeat with p in existingPeople
        try
          add p to grindGroup
          set addedOK to true
          exit repeat
        end try
      end repeat

      if not addedOK then
        -- Fallback: create a new local contact so it can be added to the group
        set newPerson to make new person with properties {first name:firstName, last name:lastName}
        make new email at end of emails of newPerson with properties {label:"Grind", value:emailAddr}
        save
        add newPerson to grindGroup
      end if
    else
      -- No existing contact — create a new one
      set newPerson to make new person with properties {first name:firstName, last name:lastName}
      make new email at end of emails of newPerson with properties {label:"work", value:emailAddr}
      add newPerson to grindGroup
    end if

    save
  end tell
end run
APPLESCRIPT
done

# ── 3. Create "Grind" mailbox in Mail.app ───────────────────────────
echo "Setting up Mail mailbox '$MAILBOX_NAME'..."

osascript <<'APPLESCRIPT'
tell application "Mail"
  -- Create mailbox under "On My Mac" if it doesn't exist
  if not (mailbox "Grind" exists) then
    make new mailbox with properties {name:"Grind"}
  end if
end tell
APPLESCRIPT

# ── 4. Create Mail rule to file Grind emails ────────────────────────
echo "Setting up Mail rule..."

# Build the AppleScript for the mail rule with all email addresses
{
  cat <<'HEADER'
tell application "Mail"
  -- Remove existing Grind rule if present, so we can recreate with updated addresses
  try
    delete rule "Grind"
  end try

  set newRule to make new rule at end of rules with properties {name:"Grind", should move message:true, should copy message:false, enabled:true}

  -- Set the destination mailbox
  set move message to mailbox "Grind" of newRule

  -- Add conditions for each email address (any match)
  set all conditions of newRule to {meets every condition:false}
HEADER

  for email in "${EMAILS[@]}"; do
    cat <<CONDITION
  make new rule condition at end of rule conditions of newRule with properties {rule type:from header, qualifier:does contain value, expression:"$email"}
CONDITION
  done

  cat <<'FOOTER'
end tell
FOOTER
} | osascript

echo ""
echo "Done! Setup complete:"
echo "  - Contacts group '$GROUP_NAME' with ${#EMAILS[@]} contact(s)"
echo "  - Mail mailbox '$MAILBOX_NAME'"
echo "  - Mail rule '$GROUP_NAME' (files matching emails into $MAILBOX_NAME)"
echo ""
echo "Note: You may need to restart Mail.app for the rule to take full effect."
