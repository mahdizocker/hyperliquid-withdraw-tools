import * as hl from "@nktkas/hyperliquid";
import { privateKeyToAccount } from "viem/accounts";
import * as dotenv from "dotenv";

dotenv.config();

// ---- 1) Load config from .env ----
const PRIVATE_KEY = process.env.PRIVATE_KEY as `0x${string}` | undefined;
const AMOUNT_HYPE = process.env.AMOUNT_HYPE_TO_WITHDRAW;

if (!PRIVATE_KEY) {
  throw new Error("PRIVATE_KEY is not set in .env");
}
if (!AMOUNT_HYPE) {
  throw new Error("AMOUNT_HYPE_TO_WITHDRAW is not set in .env");
}

// HYPE has 8 decimals on Hyperliquid:
function hypeToWei(hype: number): bigint {
  return BigInt(Math.round(hype * 100_000_000));
}

async function main() {
  const amountHype = parseFloat(AMOUNT_HYPE);
  if (isNaN(amountHype) || amountHype <= 0) {
    throw new Error("Invalid AMOUNT_HYPE_TO_WITHDRAW in .env");
  }

  const weiAmount = hypeToWei(amountHype);

  console.log(`Withdrawing ${amountHype} HYPE (${weiAmount} wei) from staking → spot`);

  // ---- 2) Set up wallet and client ----
  const account = privateKeyToAccount(PRIVATE_KEY);
  console.log(`Using address: ${account.address}`);

  const transport = new hl.HttpTransport({
    // mainnet by default
  });

  const exchClient = new hl.ExchangeClient({
    wallet: account,
    transport,
  });

  // ---- 3) Call cWithdraw ----
  const result = await exchClient.cWithdraw({
    wei: weiAmount.toString(), // send as string
  });

  console.log("cWithdraw result:");
  console.dir(result, { depth: null });
}

main().catch((err) => {
  console.error("Error in withdrawFromStaking:", err);
  process.exit(1);
});
