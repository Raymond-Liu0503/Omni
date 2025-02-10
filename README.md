# Omni

Kafka env

Zoo
cd ../
cd kafka_2.13-3.9.0
bin/zookeeper-server-start.sh config/zookeeper.properties

Kafka Server
cd ../
cd kafka_2.13-3.9.0
bin/kafka-server-start.sh config/server.properties

End Kafka Server:
rm -rf /tmp/kafka-logs /tmp/zookeeper /tmp/kraft-combined-logs

Venv
source /mnt/c/Users/raymo/Documents/Coding-Programs/KafkaProject/kafka-proj/bin/activate
cd src

Pip
/mnt/c/Users/raymo/Documents/Coding-Programs/KafkaProject/kafka-proj/bin/pip install

