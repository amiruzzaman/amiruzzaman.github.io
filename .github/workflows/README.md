### Generate a Gmail App Password

1. Go to your [Google Account settings](https://myaccount.google.com/).
2. Turn on **2-Step Verification** if it's not already enabled.
3. Once 2-Step Verification is active, go to the [App Passwords](https://myaccount.google.com/apppasswords) page.
4. Select "Mail" as the app and "Other (Custom name)" as the device. Name it something like "GitHub Actions".
5. Click **Generate**. Google will show you a 16-character password. Copy this immediately.

### Add Secrets to Your GitHub Repository

1. Go to your repository on GitHub.
2. Click on **Settings** > **Secrets and variables** > **Actions**.
3. Click **New repository secret** and add the following three secrets:

   | Secret Name | Value |
   |-------------|-------|
   | `EMAIL_USERNAME` | Your full Gmail address (e.g., `your.email@gmail.com`) |
   | `EMAIL_PASSWORD` | The 16-character App Password you just generated |
   | `EMAIL_TO` | The email address where you want to receive the notifications (can be the same as your Gmail) |

### Commit and Push

- Commit the `.github/workflows/pages-notification.yml` file to your repository's default branch (usually `main` or `master`).


### `workflow_run` Trigger
This script doesn't run on your own `push` or `deploy` event. Instead, it's triggered automatically by GitHub's internal **"pages build and deployment"** workflow. This ensures your email sends only after the official GitHub Pages process is fully complete.

### `if` Condition
The `if: ${{ github.event.workflow_run.conclusion != 'skipped' }}` line makes the email job run whether the deployment succeeded or failed.

### Dynamic Email Content
The email's subject and body dynamically pull information like the repository name, the final status (`success` or `failure`), and a direct link to the workflow run logs so you can debug any issues immediately.

### Testing the Setup
You can test the setup by making a small, empty commit to your repository. This will trigger the GitHub Pages workflow, and shortly after it finishes, you should receive the notification email in your Gmail inbox.