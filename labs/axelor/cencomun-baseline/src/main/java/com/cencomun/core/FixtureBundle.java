package com.cencomun.core;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.io.InputStream;
import java.security.MessageDigest;
import java.util.HexFormat;

/** Read immutable LAB inputs, verifying bytes before any fixture can be consumed. */
public final class FixtureBundle {
  public static final String REFERENCE = "fcf690dbc58b2b2dcf8d045c49976e3613e804cf";
  public static final String MANIFEST_SHA =
      "28496929050e7cfeea214dbf0ee5cbd589a08ab2adb60e1849877778baaf9aed";
  private static final ObjectMapper JSON = new ObjectMapper();

  public static byte[] bytes(String name) throws IOException {
    if (!name.matches("[a-z0-9-]+\\.(json|csv)")) throw new IllegalArgumentException("Invalid fixture");
    try (InputStream input = FixtureBundle.class.getResourceAsStream("/ccm-core-v1/" + name)) {
      if (input == null) throw new IOException("Missing fixture: " + name);
      return input.readAllBytes();
    }
  }

  public static JsonNode json(String name) throws IOException { return JSON.readTree(bytes(name)); }

  public static String sha(byte[] value) {
    try { return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(value)); }
    catch (java.security.NoSuchAlgorithmException e) { throw new IllegalStateException(e); }
  }

  public static int verify() throws IOException {
    if (!MANIFEST_SHA.equals(sha(bytes("manifest.json")))) throw new IOException("Manifest differs from fixed reference");
    JsonNode manifest = json("manifest.json");
    if (manifest.get("production_policy").asBoolean()) throw new IOException("Not a synthetic bundle");
    int count = 0;
    for (JsonNode entry : manifest.get("files")) {
      byte[] value = bytes(entry.get("path").asText());
      if (value.length != entry.get("bytes").asInt()
          || !sha(value).equals(entry.get("sha256").asText()))
        throw new IOException("Fixture integrity failure: " + entry.get("path").asText());
      count++;
    }
    if (count != 16 || json("coverage-required.json").get("coverage_revision").asInt() != 2
        || json("coverage-required.json").get("requirements").size() != 34)
      throw new IOException("Wrong coverage contract");
    return count;
  }

  private FixtureBundle() {}
}
