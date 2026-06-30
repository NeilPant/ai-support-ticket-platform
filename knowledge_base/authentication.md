# Authentication Support Playbook

## Password resets

Password reset links expire after 30 minutes. Ask the customer to request a fresh link and confirm that their email client is not rewriting URLs.

Do not manually disclose credentials. If account takeover risk is suspected, require identity verification before changing authentication settings.

## MFA and lockouts

Account lockouts usually clear after 15 minutes. MFA recovery should first check backup codes before disabling a factor.
