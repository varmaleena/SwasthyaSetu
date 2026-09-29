import {test,expect} from '@playwright/test';

test('fresh visitor completes actual golden report-to-receipt workflow',async({page})=>{
  await page.goto('/?workspace=1');await expect(page.getByRole('heading',{name:'The right stock.'})).toBeVisible();
  await page.screenshot({path:'../../docs/screenshots/landing.png',fullPage:true});
  await page.getByRole('button',{name:'Start interactive demo'}).click();
  await expect(page.getByRole('heading',{name:'Overview',exact:true})).toBeVisible();
  await page.screenshot({path:'../../docs/screenshots/overview.png',fullPage:true});
  await page.getByLabel('Simulated role').selectOption('custodian');
  await page.getByRole('navigation').getByRole('button',{name:/Report stock/}).click();
  await page.getByRole('button',{name:'Confirm reviewed stock',exact:true}).click();
  await expect(page.getByRole('status')).toContainText('Stock observation committed');
  await page.getByLabel('Simulated role').selectOption('planner');
  await page.getByRole('navigation').getByRole('button',{name:/Forecast & plan/}).click();
  await page.getByRole('button',{name:'Refresh analysis'}).click();
  await expect(page.getByText(/weekday median fallback|experimental censored negative binomial/)).toBeVisible();
  await page.getByRole('button',{name:'Compute transfer plan'}).click();
  await expect(page.getByText('C → A: 60 tablets')).toBeVisible();
  await page.getByRole('button',{name:'Reserve 60 from C'}).click();
  await page.getByLabel('Simulated role').selectOption('approver');
  await page.getByRole('button',{name:'Approve as D1'}).click();
  await expect(page.getByText('District sign-offs: D1')).toBeVisible();
  await page.getByLabel('Demo district').selectOption('D2');
  await page.getByRole('button',{name:'Approve as D2'}).click();
  await expect(page.getByRole('button',{name:'Dispatch stock'})).toBeVisible();
  await page.getByLabel('Simulated role').selectOption('custodian');
  await page.getByRole('button',{name:'Dispatch stock'}).click();
  await page.getByLabel('Simulated role').selectOption('receiver');
  await page.getByLabel('Demo district').selectOption('D1');
  await page.getByLabel('Received units').fill('20');
  await page.getByRole('button',{name:'Confirm receipt',exact:true}).click();
  await expect(page.getByText('partially received',{exact:true})).toBeVisible();
  await page.getByLabel('Received units').fill('40');
  await page.getByRole('button',{name:'Confirm receipt',exact:true}).click();
  await expect(page.getByText('received',{exact:true})).toBeVisible();
  await page.screenshot({path:'../../docs/screenshots/receipt.png',fullPage:true});
  await page.reload();await expect(page.getByRole('heading',{name:'Overview',exact:true})).toBeVisible();
  await page.getByRole('navigation').getByRole('button',{name:/Shipments/}).click();
  await expect(page.getByText('received',{exact:true})).toBeVisible();
});

test('mobile, language previews, offline version conflict and denied microphone',async({page,context})=>{
  await page.setViewportSize({width:390,height:844});await page.goto('/?workspace=1');
  await page.getByLabel('Interface language').selectOption('hi');await expect(page.getByText('Preview translations:')).toBeVisible();
  await page.getByLabel('Interface language').selectOption('te');await page.getByLabel('Interface language').selectOption('en');
  await page.getByRole('button',{name:'Start interactive demo'}).click();await expect(page.getByRole('heading',{name:'Overview',exact:true})).toBeVisible();
  await page.getByLabel('Simulated role').selectOption('custodian');await page.getByRole('navigation').getByRole('button',{name:/Report stock/}).click();
  await context.setOffline(true);await page.getByLabel('Base units').fill('45');await page.getByRole('button',{name:'Save offline draft'}).click();
  await expect(page.getByRole('status')).toContainText('Saved offline observation');
  await context.setOffline(false);await page.getByLabel('Base units').fill('50');await page.getByRole('button',{name:'Confirm reviewed stock',exact:true}).click();
  await expect(page.getByRole('status')).toContainText('Stock observation committed');
  await page.getByRole('button',{name:/Sync .*queued observations/}).click();
  await expect(page.getByRole('alert')).toContainText('VERSION_CONFLICT');
  await page.getByRole('button',{name:'Discard drafts and recount'}).click();
  await page.getByRole('button',{name:'Record 10 seconds'}).click();await expect(page.getByRole('alert')).toBeVisible();
  await page.screenshot({path:'../../docs/screenshots/mobile.png',fullPage:true});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBeTruthy();
});

test('scheduled replenishment requires actual confirmation and shared round persists',async({page})=>{
  await page.goto('/?workspace=1');await page.getByLabel('Demo scenario').selectOption('S01');
  await page.getByRole('button',{name:'Start interactive demo'}).click();
  await expect(page.getByRole('heading',{name:'Overview',exact:true})).toBeVisible();
  await page.getByRole('navigation').getByRole('button',{name:/Forecast & plan/}).click();
  await expect(page.getByRole('heading',{name:'Replenishments',exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Advance scenario 24 hours'}).click();
  await expect(page.getByText('Synthetic supply updated.')).toBeVisible();
  await page.getByLabel('Simulated role').selectOption('custodian');
  await page.getByRole('button',{name:'Confirm arrival as custodian'}).click();
  await expect(page.getByRole('button',{name:'Confirm arrival as custodian'})).toHaveCount(0);
  await page.getByLabel('Simulated role').selectOption('planner');
  await page.getByRole('navigation').getByRole('button',{name:/Shared modelling/}).click();
  await page.getByRole('button',{name:'Start real model round'}).click();
  await page.getByRole('button',{name:'Advance one persisted step'}).click();
  await expect(page.getByText('Step 1/3')).toBeVisible();
  await page.reload();await expect(page.getByRole('heading',{name:'Overview',exact:true})).toBeVisible();
  await page.getByRole('navigation').getByRole('button',{name:/Shared modelling/}).click();
  await expect(page.getByText('Step 1/3')).toBeVisible();
  await page.getByRole('button',{name:'Advance one persisted step'}).click();
  await expect(page.getByText('Step 2/3')).toBeVisible();
  await page.getByRole('button',{name:'Advance one persisted step'}).click();
  await expect(page.getByText('Step 3/3')).toBeVisible();
});



