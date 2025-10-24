# Deployment

## Build

```bash
docker build -f .\bot.Dockerfile -t rndintusr/fuh-winfo-discordbot:v1.1.2 .
docker push rndintusr/fuh-winfo-discordbot:v1.1.2

docker build -f .\scraper.Dockerfile -t rndintusr/fuh-winfo-discordbot-grade-scraper:v1.0.1 .
docker push rndintusr/fuh-winfo-discordbot-grade-scraper:v1.0.1

docker build -f .\plotter.Dockerfile -t rndintusr/fuh-winfo-discordbot-grade-plotter:v1.0.6 .
docker push rndintusr/fuh-winfo-discordbot-grade-plotter:v1.0.6
```

## Run

```bash
sudo systemctl daemon-reload

sudo systemctl enable --now test-scraper.timer
sudo systemctl status test-scraper.timer

sudo systemctl enable --now test-plotter.timer
sudo systemctl status test-plotter.timer

sudo systemctl enable --now prod-plotter.timer
sudo systemctl status prod-plotter.timer

sudo systemctl enable --now prod-scraper.timer
sudo systemctl status prod-scraper.timer

systemctl list-timers  --all
```
