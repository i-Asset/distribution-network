package com.github.christophschranz.iot4cpshub;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.MalformedURLException;
import java.net.ProtocolException;
import java.net.URL;
import java.util.Properties;

public class Semantics {
    private String server_uri;

    JsonObject streamObjects;
    String semantic;
    boolean verbose;
    String[] knownSemantics = new String[] {"SensorThings", "AAS"};
    String[] augmentedDSAttributes = new String[]{"thing", "client_app", "quantity"};  // augment attributes in "datastream" key
    String[] augmentedMetaAttributes = new String[]{"longitude", "latitude"};  // augment attributes in "meta" key
    boolean exitOnUnknownIotID = false;

    /**
     The Semantics constructor. Requires a stream app config, fetches and stores the required metadata for incoming
     jsonInputs
     */
    public Semantics(Properties stream_config, String semantic, boolean verbose) throws SemanticsException {
        // gather configs and store in class vars
        // if (semantic.equalsIgnoreCase("gost"))
        this.semantic = semantic;
        this.server_uri = stream_config.getProperty("SERVER_URI", "").replace("\"", "");
        this.verbose = verbose;

        // the json value is not indexed properly, restructure such that we have {iot_id0: {}, iot_id1: {}, ...}
        this.streamObjects = new JsonObject();  // set ST to jsonObject

        // Check the if the Semantic is supported, throw an exception otherwise
        boolean flag_isKnown = false;
        for (String knownSemantic: this.knownSemantics)
            if (knownSemantic.equals(semantic)) {
                flag_isKnown = true;
                break;
            }
        if (!flag_isKnown) {
            logger.error("Unknown semantic '" + semantic + "'. Choose one of:");
            for (String knownSemantic: this.knownSemantics)
                logger.error(" * " + knownSemantic);
            throw new SemanticsException("Semantic '" + semantic + "' is not known.");
        }

        logger.info("New " + semantic + "-semantic initialized.");
        logger.info(this.toString());

//        // Tests:
//        fetchFromGOST("1"); // -> single fetch, should work
//        fetchFromGOST(9); // -> single fetch, should work
//        System.out.println(sensorThingsStreams.get("1").getAsJsonObject());
//        fetchFromGOST();  // -> batch fetch, should work
//        fetchFromGOST(31232);  // -> should fail, as the id does not exist
    }

    /** toString-method
     * @return some information about the StreamQuery.
     */
    public String toString(){
        int size = 0;
        if (this.streamObjects != null)
            size = this.streamObjects.size();
        return "Semantics Object " + getClass()
                + "\n\tType: \t\t" + this.semantic
                + "\n\tServer: \t" + this.server_uri
                + "\n\tEntries: \t" + size;
    }

    /**
     * This method parses the raw String input and augments it with attributes specified in the argument
     * @return the Augmented JsonInput
     */
    public JsonObject augmentRawInput(String input) {
        // receive input string and parse to jsonObject
        return augmentJsonInput(jsonParser.parse(input).getAsJsonObject());
    }

    /**
     * This method augments the raw JsonObject input with attributes specified in the argument
     * @return the Augmented JsonInput
     */
    public JsonObject augmentJsonInput(JsonObject jsonInput) {
        // augment with AAS selected fields: all in 'datastream', 'attributes' and duplicate 'time'
        if (this.semantic.equalsIgnoreCase("aas")) {
            if (jsonInput.has("datastream")) {
                for (String att : this.augmentedDSAttributes) {
                    jsonInput.addProperty(att, jsonInput.get("datastream").getAsJsonObject().get(att).getAsString());
                }
            }
            if (jsonInput.has("attributes")) {
                for (String att : this.augmentedMetaAttributes) {
                    jsonInput.addProperty(att, jsonInput.get("attributes").getAsJsonObject().get(att).getAsDouble());
                }
            }
            jsonInput.addProperty("time", jsonInput.get("phenomenonTime").getAsString());
            if (this.verbose)
                logger.info("New message: " + jsonInput);
            return jsonInput;
        }

        // augment with SensorThings semantic
        else if (this.semantic.equalsIgnoreCase("sensorthings")) {

            // receive input string and parse to jsonObject
            String iot_id = jsonInput.get("Datastream").getAsJsonObject().get("@iot.id").getAsString();

            // if the iot_id is not already loaded, load again. Exit if it is not fetchable.
            if (streamObjects.get(iot_id) == null) {
                try {
                    fetchFromGOST(iot_id);
                } catch (SemanticsException e) {
                    e.printStackTrace();
                }
            }
            // If the iot.id is still not available, log an error and exit if wished so
            if (streamObjects.get(iot_id) == null) {
                logger.error("The datastream with @iot.id '" + iot_id + "' is not available.");
                if (this.exitOnUnknownIotID)
                    System.exit(61);
                for (String att : this.augmentedDSAttributes) {
                    jsonInput.addProperty(att, "");
                }
            } else {
                String quantity;
                for (String att : this.augmentedDSAttributes) {
                    jsonInput.addProperty(att, streamObjects.get(iot_id).getAsJsonObject().get(att).getAsString());
                }
                logger.debug("Getting new (augmented) kafka message: {}", jsonInput);
            }
            return jsonInput;
        } else
            logger.warn("The semantic " + this.semantic + " is not known.");
        return jsonInput;
    }

    /**
     *  fetches all datastreams from GOST Server and stores the mapping of the form iot.id: entry
     *  (hash-indexed) into a jsonObject, such that the entry is available with complexity O(1).
     *  default parameter -1 triggers to fetch all entries, as it is useful at the startup.
     *  */
    public void fetchFromGOST() throws SemanticsException {
        fetchFromGOST(-1);
    }
    /**
     *  receives the datastream iot_id as String. Trying to convert the String to an Integer and fetching this
     *  datastream from GOST Server. If not possible, all datastreams are fetched.
     *  */
    public void fetchFromGOST(String iot_id_str) throws SemanticsException {
        try {
            fetchFromGOST(Integer.parseInt(iot_id_str.trim()));
        } catch (NumberFormatException e) {
            logger.warn("fetchFromGOST, iot_id string couldn't be converted to integer, fetching all datastreams.");
            fetchFromGOST();
        }
    }

    /**
     *  Checks the connection to the Semantic Server and throws an error if not reachable
     *  */
    public void checkConnection() throws SemanticsException {
        if (this.semantic.equalsIgnoreCase("sensorthings")){
            checkConnectionGOST();
        } else if (this.semantic.equalsIgnoreCase("aas")) {
            checkConnectionAAS();
        } else
            logger.warn("The semantic " + this.semantic + " is not known.");
    }
    /**
     *  Checks the connection to the SensorThings Server and throws an error if not reachable
     *  */
    public void checkConnectionGOST() throws SemanticsException {
        // urlString that is appended by the appropriate mode (all ds or a specified)
        String urlString = "http://" + this.server_uri;
        logger.info("Trying to connect with " + this.semantic + "-Server at: " + urlString);

        try {
            URL url = new URL(urlString);
            HttpURLConnection conn = (HttpURLConnection) url.openConnection();
            conn.setRequestMethod("HEAD");
            conn.setConnectTimeout(5000); //set timeout to 5 seconds
            conn.setRequestMethod("GET");
            BufferedReader rd = new BufferedReader(new InputStreamReader(conn.getInputStream()));
            logger.info("Connected to " + this.server_uri);
        } catch (java.net.ConnectException | java.net.SocketTimeoutException | java.net.NoRouteToHostException e) {
            logger.warn("GOST Server at '" + this.server_uri + "' is not reachable.");
            if (!this.server_uri.contains("dashboard:8080")) {
                logger.warn("Setting gost-server to 'http://dashboard:8080' and try again.");
                this.server_uri = "dashboard:8080";
                checkConnectionGOST();
            }
            else
                logger.error("Aborting as GOST is not reachable.");
        } catch (ProtocolException e) {
            e.printStackTrace();
        } catch (java.net.UnknownHostException e) {
            logger.error("Unknown host '" + this.server_uri + "'. Aborting!");
            e.printStackTrace();
            System.exit(62);
        } catch (MalformedURLException e) {
            e.printStackTrace();
        } catch (IOException e) {
            e.printStackTrace();
        }
    }

    /**
     *  Checks the connection to the AAS Server and throws an error if not reachable
     *  */
    public void checkConnectionAAS() throws SemanticsException {
        // urlString that is appended by the appropriate mode (all ds or a specified)
        String urlString = "http://" + this.server_uri;
        logger.info("Trying to connect with " + this.semantic + "-Server at: " + urlString);

        try {
            URL url = new URL(urlString);
            HttpURLConnection conn = (HttpURLConnection) url.openConnection();
            conn.setRequestMethod("HEAD");
            conn.setConnectTimeout(5000); //set timeout to 5 seconds
            conn.setRequestMethod("GET");
            BufferedReader rd = new BufferedReader(new InputStreamReader(conn.getInputStream()));
            logger.info("Connected with the distribution-network server " + this.server_uri);
        } catch (java.net.ConnectException | java.net.SocketTimeoutException | java.net.NoRouteToHostException e) {
            logger.warn("GOST Server at '" + this.server_uri + "' is not reachable.");
            // retry with a relative name
            if (!this.server_uri.contains("registry-service:1908")) {
                logger.warn("Setting AAS-server to 'http://registry-service:1908' and try again.");
                this.server_uri = "registry-service:1908";
                checkConnectionAAS();
            }
            else
                logger.error("Aborting as the AAS-Server is not reachable.");
        } catch (ProtocolException e) {
            e.printStackTrace();
        } catch (java.net.UnknownHostException e) {
            logger.error("Unknown host '" + this.server_uri + "'. Ignoring");
            e.printStackTrace();
            /*System.exit(63);*/
        } catch (MalformedURLException e) {
            e.printStackTrace();
        } catch (IOException e) {
            e.printStackTrace();
        }
    }

    /**
         *  Fetches all datastreams from GOST Server and stores the mapping of the form iot.id: entry
         *  (hash-indexed) into a jsonObject, such that the entry is available with complexity O(1).
         *  default parameter -1 triggers to fetch all entries, as it is useful at the startup.
         *  */
    public void fetchFromGOST(int iot_id) throws SemanticsException {
        // urlString that is appended by the appropriate mode (all ds or a specified)
        String urlString = "http://" + this.server_uri;
        logger.info("Reconnect to SensorThings-Server to fetch iot.id " + iot_id);

        if (iot_id <= 0)  // fetching all datastreams for iot_id <= 0
            urlString += "/v1.0/Datastreams";
        else              // fetching a singe datastream
            urlString += "/v1.0/Datastreams(" + iot_id + ")";
//        logger.debug(urlString);

        StringBuilder result = new StringBuilder();
        try {
            URL url = new URL(urlString);
            HttpURLConnection conn = (HttpURLConnection) url.openConnection();
            conn.setRequestMethod("GET");
            BufferedReader rd = new BufferedReader(new InputStreamReader(conn.getInputStream()));
            String line;
            while ((line = rd.readLine()) != null) {
                result.append(line);
            }
            rd.close();
            JsonElement rawJsonObject = jsonParser.parse(result.toString());

            // storing all datastreams
            if (iot_id <= 0) {
                JsonArray rawJsonArray = rawJsonObject.getAsJsonObject().get("value").getAsJsonArray();
                // adding the iot.id: entry mapping to the object
                for (int i = 1; i < rawJsonArray.size(); i++) {
                    logger.info("Adding new datastream with name '" +
                            rawJsonArray.get(i).getAsJsonObject().get("name").getAsString() + "' to mappings.");
                    this.streamObjects.add(
                            rawJsonArray.get(i).getAsJsonObject().get("@iot.id").getAsString(),
                            rawJsonArray.get(i).getAsJsonObject());
                }
            }
            // adding only a single datastream
            else {
                JsonObject rawJsonDS = rawJsonObject.getAsJsonObject();
                logger.info("Adding new datastream with name '" + rawJsonDS.get("name").getAsString() +
                        "' to mappings.");
                this.streamObjects.add(
                        rawJsonDS.get("@iot.id").getAsString(),
                        rawJsonDS);
            }
        } catch (Exception e) {
            logger.error("@iot.id '" + iot_id + "' is not available on SensorThings server '" + urlString + "'.");
            logger.error("Try to restart the client application as it may use a deprecated datastream mapping!");
            checkConnectionGOST();
            if (this.exitOnUnknownIotID)
                throw new SemanticsException("@iot.id '" + iot_id + "' was not found on SensorThings server '" + urlString + "'.");
        }
    }
    /**
     * datastream objects from the semantic server are cached in memory to improve the inference time.
     * */
    public void setStreamObjects(JsonObject streamObjects) {
        this.streamObjects = streamObjects;
    }

    /**
     * create required class instances
     */
    public static Logger logger = LoggerFactory.getLogger(Semantics.class);

    public static JsonParser jsonParser = new JsonParser();
}
