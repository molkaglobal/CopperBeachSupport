# Shipping Rules Setup in Helm

1. Go to **Settings → Shipping Rules**.
2. Click **Create Rule** and name it clearly (e.g. "RM Next Day").
3. Add **Conditions**:
   - Sales Channel = Shopify / Amazon / etc.
   - Requested Service Name contains "Next Day" or "Standard".
   - Add weight/value/destination if needed.
4. Set **Actions**:
   - Courier = Royal Mail / DHL etc.
   - Service = Correct service (Tracked24, Standard, etc).
   - Packaging if needed.
5. Order rules by **priority** (top = first match).
6. Add a **fallback courier** in case of failure.
7. Test with a real/dummy order → check label and flow.
