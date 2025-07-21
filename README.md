https://github.com/termux/termux-app/releases/download/v0.118.3/termux-app_v0.118.3+github-debug_x86_64.apk


pkg install python git -y

pkg install wget -y

wget https://raw.githubusercontent.com/drbathai669/Dual2DBT/refs/heads/main/proxy.py

git clone https://github.com/drbathai669/Dual2DBT.git

cd Dual2DBT

python proxy.py

-----------------------------------------------------------
nano ~/startproxy.sh


#!/data/data/com.termux/files/usr/bin/bash
cd ~/Dual2DBT
nohup python proxy.py > /dev/null 2>&1 &


chmod +x ~/startproxy.sh

echo 'bash ~/startproxy.sh' >> ~/.bashrc
