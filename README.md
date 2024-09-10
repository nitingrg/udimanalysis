# Maya UDIM Analysis Tool

A tool to check if two material sets are sharing the same UDIM or have overlapping UVs. This is useful for Material based texturing workflow.

## Getting Started

Create a new button in Maya UI and paste this python script in it. 

## Prerequisites

Autodesk Maya 

## Installation

1. Open the script editor in Maya
2. Create a new Python tab in the bottom editor and paste the script.
3. Select all the contents on the script and middle mouse + drag into your custom shelf.
4. Click on the newly created button to open the UDIM Analysis Tool. 

## Information

This Python tool for Maya helps detect if multiple materials are sharing the same UDIM space, which is crucial for a streamlined workflow in tools like Substance Painter. When working with material-based workflows, where UDIMs (e.g., 1001, 1002) are grouped by material type, sharing UVs from different meshes with different material types (e.g., wood, stone) within the same UDIM (e.g., 1001) can cause Substance Painter to generate multiple textures for the same UDIM. This tool scans your scene and identifies such overlaps, helping you maintain an organized and efficient texture pipeline.
