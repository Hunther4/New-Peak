import { describe, it, expect } from "vitest"
import { nemFromGrade, gradeFromNem, DEMRE_NEM_GRUPO_A } from "../nemScale"

describe("DEMRE Grupo A NEM Scale", () => {
  it("has exactly 301 entries spanning 4.00 to 7.00", () => {
    expect(Object.keys(DEMRE_NEM_GRUPO_A).length).toBe(301)
  })

  it("converts key official benchmarks correctly", () => {
    expect(nemFromGrade(4.00)).toBe(100)
    expect(nemFromGrade(5.00)).toBe(415)
    expect(nemFromGrade(5.50)).toBe(572)
    expect(nemFromGrade(6.00)).toBe(713)
    expect(nemFromGrade(6.40)).toBe(828)
    expect(nemFromGrade(7.00)).toBe(1000)
  })

  it("performs reverse lookup accurately", () => {
    expect(gradeFromNem(100)).toBe(4.00)
    expect(gradeFromNem(415)).toBe(5.00)
    expect(gradeFromNem(572)).toBe(5.50)
    expect(gradeFromNem(713)).toBe(6.00)
    expect(gradeFromNem(828)).toBe(6.40)
    expect(gradeFromNem(1000)).toBe(7.00)
  })

  it("clamps boundaries gracefully", () => {
    expect(nemFromGrade(3.5)).toBe(100)
    expect(nemFromGrade(7.5)).toBe(1000)
    expect(gradeFromNem(50)).toBe(4.00)
    expect(gradeFromNem(1200)).toBe(7.00)
  })
})
