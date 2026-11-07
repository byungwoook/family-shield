package com.familyshield.app

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File
import javax.xml.parsers.DocumentBuilderFactory

class StringTableTest {
    @Test
    fun koreanHasEveryEnglishStringAndTheSamePlaceholders() {
        val english = strings(File("src/main/res/values/strings.xml"))
        val korean = strings(File("src/main/res/values-ko/strings.xml"))
        assertEquals(english.keys, korean.keys)
        val placeholder = Regex("%(\\d+\\$)?[sd]")
        english.forEach { (name, value) ->
            assertEquals(name, placeholder.findAll(value).map { it.value }.toList(), placeholder.findAll(korean.getValue(name)).map { it.value }.toList())
        }
    }

    @Test
    fun resultCopyMatchesTheDocument() {
        val english = strings(File("src/main/res/values/strings.xml"))
        assertTrue(english.getValue("result_sent").contains("confirmed they sent it"))
        assertTrue(english.getValue("result_sent").contains("Talk to %1\$s directly before sending anything."))
        assertTrue(english.getValue("result_not_sent").contains("Do not send money and do not reply"))
        assertTrue(english.getValue("result_no_number").contains("There is no verified number"))
        assertTrue(english.getValue("result_code_locked").contains("set a new check code"))
        assertTrue(english.getValue("result_number_recent").contains("last 24 hours"))
        assertTrue(english.getValue("pattern_line_green").contains("Avoid gift cards, crypto, and wire transfers"))
        assertTrue(english.getValue("claims_heading").contains("does NOT prove who it is"))
        assertTrue(english.getValue("case_dont_send").contains("Don't send money yet"))
        val korean = strings(File("src/main/res/values-ko/strings.xml"))
        assertTrue(korean.getValue("result_not_sent").contains("돈을 보내지"))
        assertTrue(korean.getValue("case_dont_send").contains("돈을 보내지"))
    }

    private fun unescape(raw: String) = raw
        .replace("\\'", "'")
        .replace("\\\"", "\"")
        .replace("\\n", "\n")
        .replace("\\@", "@")

    private fun strings(file: File): Map<String, String> {
        val builder = DocumentBuilderFactory.newInstance().newDocumentBuilder()
        val nodes = builder.parse(file).getElementsByTagName("string")
        return buildMap {
            for (i in 0 until nodes.length) {
                val node = nodes.item(i)
                put(node.attributes.getNamedItem("name").nodeValue, unescape(node.textContent))
            }
        }
    }
}
