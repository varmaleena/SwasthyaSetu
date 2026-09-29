import {defineConfig} from '@playwright/test';
export default defineConfig({testDir:'./tests',timeout:60000,workers:1,use:{baseURL:'http://localhost:5173',channel:'msedge',headless:true,viewport:{width:1440,height:1000},screenshot:'only-on-failure'},reporter:[['list'],['json',{outputFile:'../../data/evaluation/browser-results.json'}]]});
