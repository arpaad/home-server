# H.O.M.E. a Raspberry Pi-n — lépésről lépésre

Egy fázis egy ülés. Minden fázis végén van egy **✅ Ellenőrzés** — amíg az nem
jó, ne menj tovább. A `[ ]` dobozokat pipáld, ahogy haladsz.

Előfeltevések: a Pi-n Ubuntu 22.04 (64-bit) fut, a felhasználód `lucky`, a
fix IP `192.168.0.242`, van egy USB-s SSD/pendrive az adatoknak, és a
laptopodon már fut a `main`.

A Pi-n **Docker** hostolja a konténereket, nem podman: az Ubuntu 22.04
repójában lévő podman (3.4) túl régi ehhez a stackhez, a Docker hivatalos
repója viszont naprakész arm64-re. A laptopon marad a podman; a compose fájl
ugyanaz mindkettőnek.

---

## 0. Fázis — Amit a laptopon intézel el (10 perc)

- [ ] **Fix IP a routerben.** A Pi kapjon DHCP-foglalást a `192.168.0.242`-re
  a MAC-címe alapján. (Router admin → DHCP → reservation.) Így a cím
  újraindítás után sem változik.
- [ ] **DuckDNS.** Nyisd meg a https://www.duckdns.org oldalt, lépj be
  (GitHub/Google), adj hozzá egy aldomaint, pl. `pami-home` → ez lesz a
  `pami-home.duckdns.org`. Az IP mezőbe írd be: `192.168.0.242`. Igen, privát
  IP — ez így jó, kívülről senki nem ér el semmit, csak a név oldódik fel.
  **Másold ki a tokent** (a lap tetején), kelleni fog.
- [ ] **Tailscale fiók.** https://login.tailscale.com — lépj be (Google/GitHub).
  Egyelőre ennyi.

✅ **Ellenőrzés:** a laptopon `nslookup pami-home.duckdns.org` → `192.168.0.242`.

---

## 1. Fázis — Pi alap (15 perc)

SSH-zz be a Pi-re: `ssh lucky@192.168.0.242`

```bash
sudo apt update && sudo apt full-upgrade -y
sudo apt remove -y podman                      # ha fent van; a régi 3.4 csak zavarna
sudo apt install -y ca-certificates curl git rsync
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
echo "deb [arch=arm64 signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu jammy stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
sudo reboot
```

(Ubuntu 24.04-en a `jammy` helyett `noble`.)

Várj egy percet, SSH vissza.

- [ ] `docker --version` → 2x.x
- [ ] `docker compose version` → v2.x
- [ ] `systemctl is-enabled docker` → `enabled`

✅ **Ellenőrzés:** `sudo docker run --rm hello-world` kiír egy
"Hello from Docker!" szöveget.

> Mindent **root-ként** (`sudo`) futtatunk a Pi-n. Otthoni gépen ez egyszerűbb
> és a boot-sorrend is egyértelmű. (Ha nem akarsz mindig `sudo`-zni:
> `sudo usermod -aG docker lucky`, ki-be lépés — de a systemd unitok így is
> rootként futnak.)

---

## 2. Fázis — A repo a Pi-re (5 perc)

Nem kell scp. Git clone, a rendszer helyére:

```bash
sudo git clone https://github.com/arpaad/home-server.git /opt/home-server
cd /opt/home-server
```

Ha privát a repo: a Pi-n `ssh-keygen`, a publikus kulcsot add hozzá a GitHub
→ Settings → SSH keys alá, és `git@github.com:arpaad/home-server.git`-tel klónozz.

✅ **Ellenőrzés:** `ls /opt/home-server/deploy/pi/` — látod a `SETUP.md`-t.

---

## 3. Fázis — Külső tároló (10 perc)

Az adatbázis **nem** mehet az SD-kártyára. Dugd be az SSD-t.

```bash
lsblk
```

Keresd meg az eszközt (pl. `sda`). **Figyelem: ez letörli az SSD-t.**

```bash
sudo mkfs.ext4 -L home-data /dev/sda        # az eszköznevet cseréld a sajátodra
sudo mkdir -p /mnt/home-data
echo 'LABEL=home-data /mnt/home-data ext4 defaults,nofail 0 2' | sudo tee -a /etc/fstab
sudo mount -a
sudo mkdir -p /mnt/home-data/postgres /mnt/home-data/backups
```

A `nofail` fontos: ha egyszer nincs bedugva az SSD, a Pi attól még elindul.

✅ **Ellenőrzés:** `df -h /mnt/home-data` → az SSD méretét mutatja, nem az SD-t.
`sudo reboot`, SSH vissza, `df -h /mnt/home-data` → még mindig ott van.

---

## 4. Fázis — Az app konfig és első indítás (10 perc)

```bash
cd /opt/home-server
sudo cp deploy/.env.example deploy/.env
sudo nano deploy/.env
```

Állítsd be ezeket (a többit hagyd):

```
HOME_BIND_ADDRESS=127.0.0.1          # csak a Caddy éri el, az ad HTTPS-t
POSTGRES_PASSWORD=<valami hosszú>    # csak a Pi-n belül használjuk, de legyen rendes
HOME_HOUSEHOLD_MEMBERS=["Árpád","<feleséged neve>"]
HOME_DATA_DIR=/mnt/home-data
BACKUP_OFFSITE=                      # egyelőre üres, 7. fázisban töltjük ki
NTFY_TOPIC=                          # egyelőre üres, 7. fázisban
```

Mentés (Ctrl+O, Enter, Ctrl+X). Aztán:

```bash
sudo deploy/pi/install.sh
sudo systemctl start home
sudo journalctl -u home -f          # nézd, ahogy lehúzza a képet és indul; Ctrl+C ha "ok"
```

Az első indítás lehúzza a `ghcr.io/arpaad/home-server` képet (arm64), migrál,
beseedeli a magyar kezdőcsomagot.

✅ **Ellenőrzés:** `curl -s http://127.0.0.1:8080/health` →
`{"status":"ok",...}`. Meg: `curl -s http://127.0.0.1:8080/api/shopping/categories | head -c 200`
→ magyar kategóriák.

> Hiba? `sudo docker ps -a` és `sudo docker logs home-deploy-api`.

---

## 5. Fázis — HTTPS: Caddy + DuckDNS (15 perc)

A hivatalos Caddy-ből kell egy olyan build, amiben benne van a DuckDNS-modul.
A Caddy letöltőoldala ezt egy URL-ben adja:

```bash
sudo curl -fsSL -o /usr/local/bin/caddy \
  'https://caddyserver.com/api/download?os=linux&arch=arm64&p=github.com/caddy-dns/duckdns'
sudo chmod +x /usr/local/bin/caddy
/usr/local/bin/caddy version            # kiír egy verziót → jó
/usr/local/bin/caddy list-modules | grep duckdns   # "dns.providers.duckdns" → jó
sudo useradd --system --home /var/lib/caddy --create-home --shell /usr/sbin/nologin caddy 2>/dev/null || true
```

Token és domain:

```bash
sudo nano /etc/caddy/env
```

```
HOME_DOMAIN=pami-home.duckdns.org
DUCKDNS_TOKEN=<a duckdns token a 0. fázisból>
```

```bash
sudo systemctl start caddy
sudo journalctl -u caddy -f         # várj a "certificate obtained successfully" sorra; Ctrl+C
```

Az első tanúsítvány 30–90 másodperc (DNS-propagálás). Ha "DNS problem"-et
látsz, várj egy percet, `sudo systemctl restart caddy`.

✅ **Ellenőrzés:** a laptopon, **böngészőben**: `https://pami-home.duckdns.org`
→ zöld lakat, és a lista. A telefonon (otthoni wifin) ugyanez → a böngésző
felajánlja a *Hozzáadás a kezdőképernyőhöz*-t. Telepítsd. Ez a PWA.

---

## 6. Fázis — Túléli az újraindítást? (5 perc)

Ez a lényeg. Ne hidd el, próbáld ki:

```bash
sudo systemctl status home caddy --no-pager | grep -E "●|Active"
sudo reboot
```

Két perc múlva, SSH nélkül, a telefonon: nyisd meg az appot. A lista ott van.

✅ **Ellenőrzés:** a lista betölt reboot után, kézzel nem indítottál semmit.
Ha nem: `sudo systemctl status home` és `sudo journalctl -u home -b`.

---

## 7. Fázis — Mentés, ami tényleg mentés (20 perc)

A timer már be van kapcsolva (`install.sh`), óránként dumpol a
`/mnt/home-data/backups/` alá: `hourly/` (2 nap), `daily/` (1 hónap),
`monthly/` (1 év). Minden dumpot ellenőriz. De **a Pi-n lévő mentés nem
mentés** — ha a Pi meghal, vele hal. Két dolgot állíts be:

### 7a. Másolat a laptopra (Tailscale-en át, a 8. fázis után is jó)

A laptopon legyen egy `~/backups/home` mappa, és SSH-val elérhető legyen a
Pi-ről (a Pi root SSH-kulcsát add a laptop `~/.ssh/authorized_keys`-éhez:
`sudo ssh-keygen` a Pi-n, `sudo cat /root/.ssh/id_ed25519.pub`).

`deploy/.env`-ben:
```
BACKUP_OFFSITE=lucky@<laptop-tailscale-ip>:backups/home
```

### 7b. Értesítés, ha elromlik

https://ntfy.sh — nem kell fiók. Találj ki egy hosszú, nem kitalálható
témanevet (pl. `pami-home-backup-Xk29fQ`), telepítsd az ntfy appot a
telefonra, iratkozz fel rá. `deploy/.env`:
```
NTFY_TOPIC=pami-home-backup-Xk29fQ
```

Aztán próbáld ki **mindkét irányba**:

```bash
sudo systemctl start home-backup         # kézi futtatás
sudo journalctl -u home-backup -n 20     # "backup: verified", "backup: ok"
ls -la /mnt/home-data/backups/hourly/    # ott a dump
# és a laptopon: ls ~/backups/home/hourly/

# Most rontsd el szándékosan, hogy lásd, szól-e:
sudo docker stop home-deploy-db
sudo systemctl start home-backup         # ez elhasal
sudo docker start home-deploy-db
```

✅ **Ellenőrzés:** a második futás után **jött push a telefonra**. Ha nem jött,
a riasztás nem működik, és egy fél év múlva néma hibát fogsz találni.

### 7c. Visszaállítás-próba — most, amíg nincs mit elveszíteni

```bash
sudo deploy/pi/restore.sh /mnt/home-data/backups/hourly/<legfrissebb>.dump
```

✅ **Ellenőrzés:** a script a végén kiírja a tételek számát, az app megy.
Amíg ezt egyszer nem csináltad meg, nincs mentésed, csak reményed.

---

## 8. Fázis — Tailscale: elérés útközben (15 perc)

A Pi-n:

```bash
curl -fsSL https://tailscale.com/install.sh | sh
echo 'net.ipv4.ip_forward = 1' | sudo tee /etc/sysctl.d/99-tailscale.conf
sudo sysctl -p /etc/sysctl.d/99-tailscale.conf
sudo tailscale up --advertise-routes=192.168.0.0/24
```

Kiír egy linket → nyisd meg, lépj be. Aztán a **Tailscale admin konzolban**
(https://login.tailscale.com/admin/machines): a Pi gépnél → **Edit route
settings** → pipáld be a `192.168.0.0/24`-et. Enélkül a route nem él.

Telefon: Tailscale app a boltból, belépés ugyanazzal a fiókkal, kapcsold be.
A beállításokban legyen bekapcsolva a **"Use Tailscale subnets"** (Android:
Settings → Use subnet routes).

✅ **Ellenőrzés:** kapcsold ki a wifit a telefonon (mobilnet), Tailscale be,
nyisd meg `https://pami-home.duckdns.org` → **ugyanaz** a lista, zöld lakat.
Tailscale ki → nem tölt be, de az app **offline-módban** mutatja a másolatot.

A feleséged telefonjára ugyanez, ha akarja. Ha nem, otthon wifin nélküle is
megy minden.

---

## 9. Fázis — Frissítés (később, bármikor)

Amikor a laptopon merge-öltél és tag-eltél (`vX.Y.Z` → GHCR-re megy a kép):

```bash
cd /opt/home-server && sudo deploy/pi/update.sh
```

Ez `git pull` + kép lehúzás + újraindítás; a konténer migrál. Ha a
`deploy/pi/` mappa változott, előtte `sudo deploy/pi/install.sh`.

---

## Ha valami nem megy — hol nézd

| Tünet | Parancs |
|---|---|
| nem tölt be az app | `sudo systemctl status home caddy` |
| API log | `sudo docker logs home-deploy-api` |
| adatbázis log | `sudo docker logs home-deploy-db` |
| HTTPS/tanúsítvány | `sudo journalctl -u caddy -n 50` |
| mentés | `sudo journalctl -u home-backup -n 50`, `systemctl list-timers` |
| Tailscale | `sudo tailscale status` |
| helyfoglalás | `df -h /mnt/home-data` |

## Amit NE csinálj

- Ne nyiss portot a routeren. Semmit. A Tailscale nem kér ilyet.
- Ne tedd az adatbázist az SD-kártyára "csak ideiglenesen".
- Ne hagyd ki a 7c-t.
