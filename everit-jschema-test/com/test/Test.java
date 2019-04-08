package com.test;

import java.io.InputStream;

import org.everit.json.schema.Schema;
import org.everit.json.schema.loader.SchemaClient;
import org.everit.json.schema.loader.SchemaLoader;
import org.json.JSONObject;
import org.json.JSONTokener;


public class Test
{
	public static void main(String[] args) {
		String jschRoot = "com/test/";
        InputStream inStream = Test.class
						.getClassLoader()
						.getResourceAsStream(jschRoot + "/schema.json");

		JSONObject rawSchema = new JSONObject( new JSONTokener(inStream) );
		SchemaLoader schemaLoader = SchemaLoader.builder()
						.schemaClient(SchemaClient.classPathAwareClient())
						.resolutionScope("classpath://" + jschRoot)
                        .schemaJson(rawSchema)
						.build();

		Schema schema = schemaLoader.load().build();

		String jstrToValidate = "{\"a\": 1}";

		schema.validate( new JSONObject(jstrToValidate) );
	}
}
