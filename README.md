## e360 Classroom Data Logger (Precision Temperature Fork)

This repository is a fork of **Edward K. Mallon's [e360-Classroom-Data-Logger-2023](https://github.com)**. All credits for the foundational logger framework, hardware design, and core codebase belong to the initial author and the Cave Pearl Project.

## Purpose of this Fork

The aim of this fork is to extend the logger's capabilities by adding support for multiple high-precision I2C temperature sensors. This makes the logger suitable for applications requiring tighter thermal tolerances and calibration-grade accuracy.

### Supported Sensors
* **TMP117** – High-precision digital temperature sensor, accuracy not worse than ±0.1&nbsp;°C from –20&nbsp;°C to +50&nbsp;°C
* **TMP119** – Upgraded high-precision digital temperature sensor, **accuracy ±0.03&nbsp;°C (typical) from 0&nbsp;°C to 45&nbsp;°C**
* **ADT7420** – 16-bit digital temperature sensor ±0.20 °C accuracy from −10°C to +85 °C

---

## Usage & Configuration

### Sensor Compatibility
**TMP119 Users:** The TMP119 is entirely code-compatible with the TMP117. When configuring your hardware, uncomment the respective **TMP117** options in the code.

### Multi-Sensor Support

For TMP117 and TMP119, you can deploy up to **four sensors simultaneously** on the I2C bus using addresses `0x48`, `0x49`, `0x4A`, `0x4B`.

### TMP117 / TMP119 Operation Modes
To balance power efficiency with data quality, you can choose from three hardware averaging modes during setup:

| Averaging Mode | Best For | Trade-off |
| :--- | :--- | :--- |
| **No Averaging** | Minimizing power consumption | Higher noise floor |
| **8x Averaging** | General use / balanced logging | Moderate power draw |
| **64x Averaging** | Maximum thermal accuracy | Higher power consumption per sample |

*💡 **Tip:** If your logger is running on a CR2032 coin cell for long-term deployment, **No Averaging** is recommended to maximize battery life.*

---
### Data Download Utility

A convenient Python data download tool is available at `utility/e360_CavePearl_logger_data_download.py`. 

It is compatible with both **Windows** and **Linux**, and features automatic port discovery for **FT232R** (FTDI), **CP2102** and **CH340** USB-to-serial converters. The utility converts the UNIX timestamp to ISO8601 datetime, exports data into a cleaned .tsv (Tab-Separated Values) file. Modify it according your own requirements.

## Disclaimer regarding the Fork
⚠️ **Important Notice:** Only basic tests have been performed so far. This code is provided as-is. Use it entirely at your own risk and responsibility.


--------------------------



![banner image](https://github.com/EKMallon/The-e360-Student-Built-Data-Logger/assets/7884030/48f75f8c-3236-4a68-9ae2-6572afddc3ce)


This program supports an ongoing series of DIY 'Classroom Logger' tutorials from Edward Mallon & Dr. Patricia Beddows at the Cave Pearl Project. The idea is to provide a starting point for student projects in environmental monitoring courses and/or thesis level research.</br>
The tutorial for this logger: [The e360: A Classroom Data Logger for Science](https://thecavepearlproject.org/2023/12/01/the-e360-a-10-classroom-data-logger-for-science/)</br>
has a companion video [2-Module Data Logger Build Video (90min w Commentary)](https://youtu.be/_LEFM4l9m5c)

<figure><img  align="right" width="400" height="240" src="images/20231128_e360_schematic_400x240.png"></figure>
The code has support for a built-in NTC / LDR combination, Bmp280, BH1750, and PIR sensors. These are enabled / disabled by uncommenting define statements at the beginning of the code. Each sensor enabled after the single-byte LowBat & RTCtemp defaults contributes two additional bytes per sampling event because every sensor reading gets stored in a 16-bit integer. The total bytes per saved per record must total 1, 2, 4, 8 or 16 only. Modifying the logger base code for a new type of sensor requires edits only at the areas indicated by call out numbers on the following flow charts. These are labeled with comments: STEP1, STEP2, STEP3, etc. so you can locate those sections with the Find function in the IDE.  They are surrounded by rows of ++PLUS++ symbols:</br>
>//++++++++++++++++++++++++++++++++++++++++++++++++++++</br>
>// STEP1 : #include libraries & Declare Variables HERE</br>
>//++++++++++++++++++++++++++++++++++++++++++++++++++++</br>
</br>

![Image](https://github.com/user-attachments/assets/90d93949-34fe-46d0-b0b0-d4a1093a353c)
If all you do is enable the supported sensors via defines at the start of the program you won't have to deal with the low-level storage details.
![image](https://github.com/EKMallon/e360-Student-Data-Logger-2023/assets/7884030/29d781fe-6e29-4e28-8342-0259748029fe)

 However to add new sensors you'll need to understand the I2C transaction that transfers those sensor readings into the EEprom at the end of the main loop. This involves dividing your sensor variables into 8-bit pieces and adding those bytes to the wire transfer buffer. This is accomplished with bit-math operations or via the lowByte & highByte macros.  The general pattern when sending bytes to an I2C EEprom is:</br>

```
Wire.beginTransmission(EEpromAddressonI2Cbus);
Wire.write(highByte(memoryAddress));
Wire.write(lowByte(memoryAddress));
loByte = lowByte(SensorReadingVariable); Wire.write(loByte);
hiByte = highByte(SensorReadingVariable); Wire.write(hiByte);
```

**add more Wire.write statements here as needed**  
You can ONLY add a total of 1, 2, 4, 8 or 16 DATA bytes to the I2C transaction. Powers of two increments are required because the recorded data must align with page boundaries inside the EEprom.

```
Wire.endTransmission();
```

The key insight here is that the wire library is only loading a memory buffer until Wire.endTransmission() is called. So it does not matter how much time you spend doing calculations, or slicing the variables, so long as you don't try and start another I2C transaction while you are still in the middle of this one. Once that buffer is physically sent over the wires, the EEprom enters a self-timed writing sequence and the logger reads the rail voltage while the CR2032 is under load. </br>

The data download function in setup retrieves those separate bytes and concatenates them back into the original integers - so the sequence of operations in the sendData2Serial function -STEP6- must exactly mirror the byte-order used to load the EEprom in the main loop.

---

In 2026: New configuration options were added to the start-up menu [ accessed via the IDEs Serial Monitor window ] 
![image](https://github.com/EKMallon/e360-Classroom-Data-Logger-2023/blob/main/images/2026_StartMenuOptionScreen.jpg)

