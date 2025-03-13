import re
import time
import random
import platform
import requests
import subprocess
from datetime import datetime
from collections import defaultdict


class SlurmMonitor:
    def __init__(self):
        self.slack_webhook_url = "<WEB HOOK HERE>"
        self.check_interval = 60
        self.previous_users = None

        self.known_users = {"tepp5511": "<@meren>",
                            "elgo4396": "<@iva>",
                            "patz5242": "<@florian>",
                            "bube0466": "<@mete>",
                            "gegu0440": "<@xixi>",
                            "larm6177": "<@sarah>",
                            "tele0144": "<@alex>",
                            "xuaf2725": "<@katy>",
                            "sore6591": "<@avril>",
                            "jert0988": "<@amy>",
                            "zina4710": "<@jessika>",
                            "mueb6691": "Matthias Weitz"}

    @staticmethod
    def parse_time(time_str):
        """
        Converts time string from various squeue output formats (D-H:M:S, H:M:S, M:S, S) to a human-readable format.
        """

        if '-' in time_str:
            day, rest = time_str.split('-')
            day = int(day)
            hours, minutes, seconds = list(map(int, rest.split(':')))
        else:
            parts = list(map(int, time_str.split(':')))
            if len(parts) == 3:  # H:M:S format
                hours, minutes, seconds = parts
                days = 0
            elif len(parts) == 2:  # M:S format
                minutes, seconds = parts
                hours = 0
                days = 0
            elif len(parts) == 1:  # S format
                seconds = parts[0]
                minutes = 0
                hours = 0
                days = 0

        readable_time = []
        if days:
            readable_time.append(f"{days}d")
        if hours:
            readable_time.append(f"{hours}h")
        if minutes:
            readable_time.append(f"{minutes}m")
        if seconds:
            readable_time.append(f"{seconds}s")

        return ' '.join(readable_time) if readable_time else "0s"


    def get_random_slack_notification_for_jobs(self, user, event):
        """Generates a random SLURM notification message for Slack for new/finished jobs on ROSA by a given user."""

        new_job_messages = [
            f"There are new jobs on ROSA for *{user}*! Buckle up! :rocket:",
            f"Heads up, *{user}*! Fresh jobs just landed on ROSA! :eyes:",
            f"Hey *{user}*, your jobs just hit the queue! :construction_worker:",
            f"New ROSA jobs incoming for *{user}*! :computer:",
            f"*{user}* has new jobs running on ROSA. :chart_with_upwards_trend:",
            f"Looks like *{user}* is keeping ROSA busy again! :hourglass_flowing_sand:",
            f"Incoming workload detected! *{user}* has jobs in the queue! :robot_face:",
            f"New jobs for *{user}* on ROSA. :gear:",
            f"Brace yourselves, *{user}*’s jobs are running on ROSA! :zap:",
            f"Guess who’s back? It’s *{user}* with more jobs on ROSA! :sunglasses:",
            f"ROSA’s got work to do! *{user}* just submitted new jobs! :fire:",
            f"Hey *{user}*, your jobs are officially in action on ROSA! :runner:",
            f"New SLURM jobs detected! *{user}* is on a roll? :clipboard:",
            f"Great news: *{user}* has new jobs in ROSA’s pipeline! :brain:",
            f"All systems go! *{user}* has jobs running on ROSA! :rocket:",
            f"New jobs alert! *{user}* is back at it on ROSA! :alarm_clock:",
            f"Time to put ROSA to work! *{user}* just submitted some jobs! :computer_mouse:",
            f"Processing request confirmed! *{user}*’s jobs are in the system! :white_check_mark:"
        ]

        finished_job_messages = [
            f"Mission accomplished! All ROSA jobs by *{user}* are done! :tada:",
            f"No more jobs for *{user}*! ROSA can finally take a breather. :relieved:",
            f"*{user}*’s jobs have wrapped up! Time to celebrate! :champagne:",
            f"That’s a wrap! *{user}* has no more jobs on ROSA! :clapper:",
            f"All jobs done! *{user}* can rest easy now. :sleeping:",
            f"ROSA just finished running all jobs by *{user}*! Nice work! :muscle:",
            f"Break time! *{user}*’s jobs are all completed. :coffee:",
            f"All clear! *{user}* has no active jobs on ROSA. :white_check_mark:",
            f"Another batch bites the dust! *{user}* is all done. :boom:",
            f"Processing complete! *{user}*’s jobs are no more! :robot_face:",
            f"Compute cycle complete! *{user}* has finished all jobs! :star:",
            f"All of *{user}*’s jobs have crossed the finish line! :checkered_flag:",
            f"ROSA says goodbye to *{user}*’s jobs. Until next time! :wave:",
            f"No more crunching numbers for *{user}*! Jobs are done! :bar_chart:",
            f"All of *{user}*’s computations are history! :scroll:",
            f"Ding! *{user}*’s job queue is empty now! :bell:",
            f"Nothing left in the ROSA queue for *{user}*! :ghost:",
            f"Job execution complete! *{user}*’s tasks are finished! :white_check_mark:",
            f"Well done, *{user}*! All your ROSA jobs are complete. :medal_sports:",
            f"ROSA is free from *{user}*'s jobs! :bird:"
        ]

        if event == "new":
            return random.choice(new_job_messages)
        elif event == "finished":
            return random.choice(finished_job_messages)
        else:
            raise ValueError("Invalid event type. Use 'new' or 'finished'.")


    def get_slurm_queue(self):
        """Fetch the current slurm queue status using squeue."""

        try:
            result = subprocess.run(["squeue", "-A", "agecodatasci", "-o", "%11i %35j %20u %5C %13m %8T %10M %9l %6D %R"],
                                    capture_output=True, text=True, check=True)
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            return f"Error fetching slurm queue: {e}"


    def get_known_user_name(self, user):
        """Replaces ROSA user ID with known user ID when applicable"""

        return self.known_users[user] if user in self.known_users else user


    def get_current_users(self, job_output):
        """Extracts a set of unique users from the Slurm queue output."""

        lines = job_output.strip().split('\n')[1:]

        users = set([self.get_known_user_name(u) for u in [re.split(r'\s+', line, maxsplit=9)[2] for line in lines]])

        return users


    def check_user_changes(self):
        """Check for new and finished users and send Slack notifications."""

        # get a fresh output
        output = self.get_slurm_queue()
        current_users = self.get_current_users(output)

        # find out hat has changed
        new_users = current_users - self.previous_users
        finished_users = self.previous_users - current_users

        for user in new_users:
            self.send_slack_message(self.get_random_slack_notification_for_jobs(user, 'new'))

        for user in finished_users:
            self.send_slack_message(self.get_random_slack_notification_for_jobs(user, 'finished'))

        self.previous_users = current_users


    def summarize_jobs(self):
        """Summarizes job statistics per user based on the provided job output."""

        job_output = self.get_slurm_queue()

        lines = job_output.strip().split('\n')

        job_data = []
        for line in lines[1:]:
            parts = re.split(r'\s+', line, maxsplit=9)
            job_data.append({
                'JOBID': parts[0],
                'NAME': parts[1],
                'USER': parts[2],
                'CPUS': int(parts[3]),
                'STATE': parts[5],
                'TIME': self.parse_time(parts[6]),
            })

        user_jobs = defaultdict(list)
        for job in job_data:
            user_jobs[job['USER']].append(job)

        summaries = []
        for user, jobs in user_jobs.items():
            user = self.get_known_user_name(user)
            total_jobs = len(jobs)
            total_cpus = sum(job['CPUS'] for job in jobs)
            longest_job = max(jobs, key=lambda x: x['TIME'])
            most_recent_job = min(jobs, key=lambda x: x['TIME'])

            if total_jobs == 1:
                summary = (f"> *{user}* has a single job, _{longest_job['NAME']}_, that is using a total of *{total_cpus}* "
                           f"{'CPUs' if total_cpus > 1 else 'CPU'} and has been running for *{longest_job['TIME']}*.")
            else:
                summary = (f"> *{user}* has *{total_jobs}* jobs using a total of *{total_cpus}* CPUs. "
                           f"The longest job,  _{longest_job['NAME']}_ has been running for *{longest_job['TIME']}* "
                           f"and their most recently started job is _{most_recent_job['NAME']}_.")

            summaries.append(summary)

        jobs_summary = '\n\n'.join(summaries)

        if len(jobs_summary):
            message = f"""A *status update* from ROSA (by <@rosalind> on head node _{platform.node()}_ at *{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}*)\n\n{jobs_summary}"""
            self.send_slack_message(message)


    def send_slack_message(self, message):
        """Send a message to Slack using the webhook."""
        payload = {"text": message}
        response = requests.post(self.slack_webhook_url, json=payload)
        return response.status_code, response.text


    def run(self):
        """Main loop to check the Slurm queue and send updates to Slack."""

        output = self.get_slurm_queue()
        self.previous_users = self.get_current_users(output)

        while True:
            if True:
                # runs every minute
                self.check_user_changes()

            if int(time.time()) % 21600 < 60:
                # runs every 6 hour-cycle
                self.summarize_jobs()

            time.sleep(self.check_interval)


if __name__ == "__main__":
    monitor = SlurmMonitor()
    monitor.run()
