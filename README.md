Rosalind is a bot that sends updates to a Slack channel regarding the HPC usage. It sends us regular updates that look like this:


<img src="https://github.com/user-attachments/assets/21fecc89-8576-426a-abda-e694b7a8b217" width="450px" />

If you want to give it a go, you need to

1. Have a webhook `rosalind` can use. For which you will need to [create a Slack App](https://api.slack.com/apps). Creating a Slack App is very simple, and it is explained in various resources. Essentially, [THIS](https://github.com/user-attachments/assets/a45dc7bf-ab87-4af9-8d1a-5c33085a4c96) is how your [Slack Apps](https://api.slack.com/apps) page should look like (you can call it anything you want, of course, and it doesn't have to be called 'rosalind'), with [these](https://github.com/user-attachments/assets/d9ad9f3a-7089-4e48-9f8a-6be6a0f6bb1a) permissions.

2. Add your new app to your Slack workspace (such as Meren Lab). The relevant page should look like [this](https://github.com/user-attachments/assets/f2f2bd8c-3239-4908-a219-568ff4c64161).

3. Copy the webhook by clicking the "Incoming webhooks" line as [shown here](https://github.com/user-attachments/assets/cebd52af-da85-4a37-9bbf-4990d1ff8963).

4. Login to your server, and get a copy of the codebase on your server:

```bash
mkdir -p ~/github
cd ~/github
git clone https://github.com/merenlab/rosalind.git
```

5. Install PyYAML (used to read the config file):

```bash
python -m pip install pyyaml
```

6. Copy the template config and fill it with your webhook (and bot token if you want file uploads) plus other preferences:

```bash
cd ~/github/rosalind
cp config.yaml.template config.yaml
# edit config.yaml to set webhook, slack_token (optional), slack_channel (ID preferred; name ok with or without #), cluster name, quiet days, user map, and (only if you know what you're doing) usage_log_path/usage_retention_days
```

7. Run `rosalind`:

```bash
cd ~/github/rosalind
./rosalind --overall-summary-at-start
```

8. You can also run `rosalind` forever on the head node of your slurm environment using `screen`, so you can safely logout while it continues to send updates to your Slack environment.

---

We didn't think anyone would use `rosalind` other than us, so we didn't much effort into it. But it has been extremely usfeul for us to keep a passive eye on our HPC activity and load. So you should feel free to try it, and please reach out to us if you have any questions. If there is demand, meren promises to learn how to make `rosalind` and _installable_ app, so everything on this page can be much more elegant compared to how they are right now :p
