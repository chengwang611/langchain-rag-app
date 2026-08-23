

def dfs(i:int,nums : list[int],choices:list[int]) :
    if i ==len(nums) :
        if len(choices) ==2 :
            print(choices)
        return
    choices.append(nums[i])
    dfs(i+1,nums,choices)
    choices.pop()
    dfs(i+1,nums,choices)

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    print("Running sample ingestion and review process...")
    nums =[1,2,3,4,5,6,7,8,9]. 10
    choices = []
    dfs(0,nums,choices)

if __name__ == "__main__":
    main()
